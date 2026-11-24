# Taints & Tolerations

## The idea

* **Taint** → on a **node** → "keep out unless you have a pass"
* **Toleration** → on a **Pod** → the pass that lets it ignore a matching taint
* Analogy → hotel → taint = a sign on a room's door ("reserved"), toleration = the guest's pass, scheduler = the receptionist who reads both
* A Pod with no matching toleration is not placed on a tainted node
* **A toleration only allows, it never attracts** → a Pod with a toleration can still land on any untainted node → to send a Pod **to** a node use `nodeSelector` / node affinity

## When they're used

| Use | How |
|---|---|
| Protect the control plane | kubeadm / kind add `node-role.kubernetes.io/control-plane:NoSchedule` |
| Dedicated GPU nodes | Taint GPU nodes (`nvidia.com/gpu=present:NoSchedule`) → only ML Pods tolerate it → GKE / EKS add it to GPU node pools |
| Node pool per team / workload | Taint the pool (`team=payments:NoSchedule`) → only that team's Pods tolerate it |
| Spot / preemptible nodes | Taint them → only Pods that survive sudden shutdown (batch jobs) tolerate it |
| Maintenance | `kubectl cordon` adds `node.kubernetes.io/unschedulable:NoSchedule` |
| Node health | Kubernetes taints unhealthy nodes by itself → `not-ready`, `unreachable`, `memory-pressure`, `disk-pressure`, `pid-pressure` |
| Per-node agents | DaemonSets (log shippers, monitoring, CNI) carry broad tolerations to run on every node |

## Taints

### Format

```
key=value:effect          →  storage=ssd:NoSchedule
key:effect                →  node-role.kubernetes.io/control-plane:NoSchedule   (value is optional)
```

### The three effects

| Effect | New Pods without toleration | Running Pods without toleration |
|---|---|---|
| `NoSchedule` | Not placed | Stay |
| `PreferNoSchedule` | Avoided, but used if nothing better fits | Stay |
| `NoExecute` | Not placed | **Evicted** |

* Mild → harsh → **Prefer → No → Execute**

### Commands

```bash
kubectl taint nodes my-new-cluster-worker storage=ssd:NoSchedule        # add
kubectl taint nodes my-new-cluster-worker storage=ssd:NoSchedule-       # remove (trailing -)
kubectl taint nodes my-new-cluster-worker storage-                      # remove every taint with key storage
kubectl taint nodes my-new-cluster-worker storage=nvme:NoSchedule --overwrite   # change the value

kubectl describe node my-new-cluster-worker | grep -i taint
kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints
```

* One node can have many taints → `describe` lists them one per line under `Taints:`

## Tolerations

### Fields → K-O-V-E

* **K**ey, **O**perator, **V**alue, **E**ffect → "**K**eep **O**ut, **V**ery **E**ffective"

```yaml
spec:
  tolerations:
  - key: "storage"          # Keep
    operator: "Equal"       # Out
    value: "ssd"            # Very
    effect: "NoSchedule"    # Effective
```

* Taint has no operator → `key=value:effect` | toleration adds the operator
* Lives under `spec` of the Pod → in a Deployment → `spec.template.spec.tolerations`
* Field help without docs → `kubectl explain pod.spec.tolerations`

### Operators

| Operator | Matches when |
|---|---|
| `Equal` (default) | Key **and** value are the same as the taint's |
| `Exists` | Key is the same → value ignored → leave `value` out (K-O-E) |

```yaml
# any storage taint → storage=ssd and storage=hdd both tolerated
- key: "storage"
  operator: "Exists"
  effect: "NoSchedule"
```

### Matching rules

* Key, value (for `Equal`) **and** effect must all match
* Effect left empty → matches **all** effects of that key
* Key empty + `operator: Exists` → matches **every** taint on every node → what DaemonSets use

```yaml
tolerations:
- operator: "Exists"
```

* A node with several taints → the Pod must tolerate **every** one of them → one missing = node blocked
* A toleration for a taint that exists on no node → does nothing → the Pod behaves like a Pod with no tolerations

### `tolerationSeconds` (NoExecute only)

```yaml
- key: "maint"
  operator: "Equal"
  value: "true"
  effect: "NoExecute"
  tolerationSeconds: 60
```

* Pod may stay on the `NoExecute` node for 60 s after the taint appears → then evicted
* No `tolerationSeconds` → stays forever

### Tolerations added automatically

```bash
kubectl get po <pod> -o yaml | grep -A3 tolerations
#  - key: node.kubernetes.io/not-ready
#    effect: NoExecute
#    tolerationSeconds: 300
#  - key: node.kubernetes.io/unreachable
#    effect: NoExecute
#    tolerationSeconds: 300
```

* Added to every Pod by an admission plugin (`DefaultTolerationSeconds`)
* Meaning → if my node goes not-ready or unreachable, wait 5 minutes before evicting me → avoids moving Pods on a short network blip
* DaemonSet Pods get these with no time limit, plus the pressure / unschedulable taints → so they keep running on unhealthy or cordoned nodes

## How the scheduler uses them

* The scheduler works in two steps:
    * **Filter** (hard rules) → drop nodes the Pod isn't allowed on → untolerated `NoSchedule` and `NoExecute` taints act here
    * **Score** (soft rules) → rank the remaining nodes → untolerated `PreferNoSchedule` taints lower a node's score → also free resources, image already on the node, spreading replicas
* A tolerated taint gives a node **no bonus** → after filtering, a tainted node the Pod tolerates and an untainted node are equal as far as taints go
* Taints are checked **only by the scheduler** → a Pod with `nodeName` set skips them (except `NoExecute`, which evicts after the Pod runs) → see [Manual Scheduling & Static Pods](manual-scheduling-and-static-pods.md)

## Where a Pod can go → worked example

| Node | Taint |
|---|---|
| Green | `color=green:NoSchedule` |
| Blue | `color=blue:PreferNoSchedule` |
| Purple | `color=green:NoExecute` |
| Plain | none |

| Pod | Green | Blue | Purple | Plain |
|---|---|---|---|---|
| No toleration | ✗ | low score | ✗ | ✓ |
| Tolerates `color=yellow` | ✗ | low score | ✗ | ✓ |
| Tolerates `color=green:NoSchedule` | ✓ | low score | ✗ (effect differs) | ✓ |
| Tolerates `color=green`, effect empty | ✓ | low score | ✓ | ✓ |
| Tolerates `color=blue:PreferNoSchedule` | ✗ | ✓ | ✗ | ✓ |

* Yellow → no node has a yellow taint → the toleration is useless → same as no toleration
* Green Pod with 10 replicas → spreads over Green **and** Plain → not "Green first" → tolerating a taint doesn't make a node preferred
* Blue Pod → tolerates the blue taint → Blue gets no penalty → Blue and Plain are equal → replicas split between them
* Existing Pods → Green and Blue ones stay when the taint is added | Purple ones without a matching `NoExecute` toleration are evicted

## Reserving nodes properly → taint + affinity

* Goal → Green nodes only for Project A, and Project A only on Green nodes
* Taint + toleration alone → keeps other Pods **off** Green ✓ → but Project A Pods can still land on Plain ✗
* `nodeSelector` / affinity alone → pulls Project A **onto** Green ✓ → but other Pods can still land on Green ✗
* Both together → full isolation

```bash
kubectl taint nodes my-new-cluster-worker color=green:NoSchedule
kubectl label nodes my-new-cluster-worker color=green
```

```yaml
spec:
  nodeSelector:
    color: green
  tolerations:
  - key: "color"
    operator: "Equal"
    value: "green"
    effect: "NoSchedule"
```

* Taint = push others away | label + selector = pull mine in

## Debugging a Pending Pod

```bash
kubectl describe po <pod> | tail -5
# 0/3 nodes are available: 1 node(s) had untolerated taint {node-role.kubernetes.io/control-plane: },
#   1 node(s) had untolerated taint {storage: ssd}, 1 node(s) had untolerated taint {storage: hdd}.
```

* Read each part → which taint blocked which node → add the toleration, or remove the taint if it was left from a test
* Check all nodes' taints in one go → `kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints`
* Common cause in real clusters → a forgotten test taint, a cordoned node, or a node with `disk-pressure` / `memory-pressure`

## Lab: one taint per worker

```bash
kubectl taint nodes my-new-cluster-worker storage=ssd:NoSchedule
kubectl taint nodes my-new-cluster-worker2 storage=hdd:NoSchedule

kubectl run plain --image=nginx
kubectl get po plain                     # Pending → every node is tainted (control plane too)
kubectl describe po plain | tail -3      # untolerated taint per node
kubectl delete po plain
```

```yaml
# deploy.yaml → tolerates only ssd
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ssd-deploy
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ssd
  template:
    metadata:
      labels:
        app: ssd
    spec:
      tolerations:
      - key: "storage"
        operator: "Equal"
        value: "ssd"
        effect: "NoSchedule"
      containers:
      - name: nginx
        image: nginx
```

```bash
kubectl apply -f deploy.yaml
kubectl get po -o wide                   # all on worker → the only node whose every taint is tolerated
```

* Looks like the toleration "pulled" Pods to worker → only because every other node was tainted → untaint worker2 and they can land there too

## Lab: multiple taints per node

```bash
kubectl taint nodes my-new-cluster-worker env=prod:NoSchedule
kubectl taint nodes my-new-cluster-worker2 env=dev:NoSchedule
```

```yaml
    spec:
      tolerations:
      - key: "storage"
        operator: "Exists"
        effect: "NoSchedule"
      - key: "env"
        operator: "Equal"
        value: "prod"
        effect: "NoSchedule"
```

* worker → `storage=ssd` ✓ + `env=prod` ✓ → allowed
* worker2 → `storage=hdd` ✓ + `env=dev` ✗ → blocked
* Pods already running on a node when a `NoSchedule` taint is added → keep running

## Lab: NoExecute eviction

```bash
kubectl run evict-me --image=nginx
kubectl get po -o wide                                              # note the node
kubectl taint nodes <that-node> maint=true:NoExecute
kubectl get po -w                                                   # evict-me is terminated → a bare Pod is not recreated
kubectl taint nodes <that-node> maint=true:NoExecute-
```

* Pods owned by a Deployment get recreated on another node | bare Pods are just gone

## Cleanup

```bash
kubectl taint nodes my-new-cluster-worker storage- env-
kubectl taint nodes my-new-cluster-worker2 storage- env-
kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints   # only the control-plane taint left
```

!!! tip "Quick revision"

    * Taint on node = keep out | toleration on Pod = pass | a pass allows, never attracts
    * Taint format → `key=value:effect` | remove with a trailing `-`
    * Effects → `PreferNoSchedule` (soft) → `NoSchedule` (no new Pods) → `NoExecute` (no new Pods + evict running ones)
    * Toleration fields → K-O-V-E → key, operator, value, effect
    * `Equal` (default) = key + value match | `Exists` = key only | empty key + `Exists` = tolerate everything
    * Empty effect in a toleration = matches all effects of that key
    * Node with several taints → Pod must tolerate all of them
    * `tolerationSeconds` → only with `NoExecute` → how long to stay before eviction
    * Every Pod auto-tolerates `not-ready` / `unreachable` for 300 s
    * Scheduler → filter (NoSchedule, NoExecute) then score (PreferNoSchedule) → a tolerated taint gives no bonus
    * Dedicated nodes → taint + toleration **and** label + nodeSelector / affinity

!!! question "Interview points"

    * What are taints and tolerations? → a taint on a node repels Pods; a toleration on a Pod lets it be scheduled onto a node with a matching taint
    * Does a toleration make a Pod run on the tainted node? → no, it only allows it; to attract a Pod to a node use nodeSelector or node affinity
    * What are the three taint effects? → NoSchedule blocks new Pods, PreferNoSchedule avoids the node if possible, NoExecute blocks new Pods and evicts running ones that don't tolerate it
    * What happens to running Pods when a NoSchedule taint is added? → nothing, they keep running; only NoExecute evicts
    * Difference between Equal and Exists? → Equal needs key and value to match; Exists only needs the key and ignores the value
    * What does a toleration with only operator Exists do? → tolerates every taint, which is how DaemonSets run on all nodes
    * What is tolerationSeconds? → for NoExecute taints, how long a Pod may stay on the node after the taint appears before it is evicted
    * Why do Pods have not-ready and unreachable tolerations by default? → the DefaultTolerationSeconds admission plugin adds them with 300 seconds so Pods aren't evicted on a short node outage
    * Why can't normal Pods run on the control plane? → kubeadm taints it with node-role.kubernetes.io/control-plane:NoSchedule to protect the API server and etcd
    * A node has two taints and the Pod tolerates one, can it schedule there? → no, the Pod must tolerate every taint on the node
    * How do you remove a taint? → kubectl taint nodes node key=value:effect with a trailing dash, or key- to remove all taints with that key
    * How do you dedicate nodes to one team? → taint the nodes so other Pods stay off, and add a label plus nodeSelector or affinity with a toleration so the team's Pods go there
    * How does the scheduler use taints? → NoSchedule and NoExecute taints filter nodes out; PreferNoSchedule lowers a node's score
    * A Pod is Pending with untolerated taint, what do you do? → read kubectl describe pod events, check the node taints, then add the toleration or remove a stale taint
    * How does kubectl cordon relate to taints? → cordon marks the node unschedulable and adds the node.kubernetes.io/unschedulable:NoSchedule taint
