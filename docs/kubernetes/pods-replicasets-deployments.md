# Pods, ReplicaSets & Deployments

## Nodes vs Pods

* **Node** → a machine (physical server, VM, or in `kind` a Docker container pretending to be a machine) → gives CPU, RAM, disk, network
* **Pod** → my app running on that machine
* Analogy → node = apartment building | Pod = a flat inside it | containers = the people living in the flat
* One node holds many Pods → the scheduler decides which building each new flat goes into

| | Node | Pod |
|---|---|---|
| What | A machine | An app instance |
| Contains | Many Pods | One or more containers |
| Created by | Me / the cloud / `kind` | Kubernetes (usually through a Deployment) |
| Lifespan | Long (days, months) | Short (can be replaced any time) |
| Command | `kubectl get nodes` | `kubectl get pods` |

## Pod

* Smallest thing Kubernetes runs → Kubernetes never runs a bare container, always a Pod
* Wraps **one or more containers** that:
    * share one **network namespace** → same IP, same ports, talk to each other over `localhost`
    * can share **volumes** → same files
* Usually one main container per Pod | extra containers = helpers (sidecars: log shipper, proxy)
* Every Pod gets its own IP inside the cluster (given by the CNI plugin)
* **Pods are disposable** → a bare Pod that dies or whose node dies is gone for good, nobody recreates it
* So in production → never create bare Pods, let a Deployment manage them

### How containers in a Pod share the network

* Each Pod has its own network namespace → own IP, interfaces, routing table
* A tiny **pause container** starts first and just holds that namespace open
* App containers join the pause container's network namespace → that is why they share one IP
* Pods are isolated from each other's networks but can reach each other by Pod IP
* Linux namespaces explained in [Container Runtime Internals](container-runtime.md)

## ReplicaSet

* One job → **keep exactly N copies of a Pod running**
* Keeps counting:
    * only 2 running → creates 1
    * 4 running → deletes 1
    * 3 running → does nothing
* Same reconciliation loop as the rest of Kubernetes
* Finds "its" Pods by **labels**, not by name

```yaml
apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: web-rs
spec:
  replicas: 3              # how many
  selector:
    matchLabels:
      app: web             # which labels to count
  template:                # what a new Pod looks like
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: nginx
        image: nginx
```

* Three parts → `replicas` (how many) | `selector` (which labels to count) | `template` (blueprint for new Pods)

### The label gotcha

* Counts by labels → a bare Pod I create with `app=web` gets counted as one of its 3 → the ReplicaSet deletes one Pod to get back to 3
* Remove the label from one of its Pods → it stops counting that Pod → creates a new one → the old Pod keeps running, orphaned
* It does not care who created a Pod, only what label it carries
* It doesn't check what's *inside* the Pod either → a 2-container Pod with `app=web` gets adopted even though the template has 1 container
* Adoption is recorded on the Pod → `ownerReferences` → deleting the ReplicaSet deletes adopted Pods too

```bash
kubectl get pod <pod> -o jsonpath='{.metadata.ownerReferences[0].name}{"\n"}'   # which RS owns it
```

### Many ReplicaSets per cluster

* A cluster runs as many ReplicaSets as it needs → usually one per app version
* Names → unique per namespace (`web-rs` can exist in `default` and in `dev`)
* Selectors → must not overlap → two ReplicaSets selecting `app=web` fight over the same Pods → give each app its own label
* A ReplicaSet lives in one cluster → other clusters know nothing about it
* Cluster ≠ node → the ReplicaSet's Pods are in one cluster but the scheduler spreads them across its nodes → one machine dies, the rest keep serving

### Why I don't use ReplicaSets directly

* A ReplicaSet can keep count but **can't update** → change the image in its template → existing Pods keep the old image, only new Pods get the new one
* That is why a Deployment sits on top of it

## ReplicationController vs ReplicaSet

* **ReplicationController (RC)** → the original, same job (keep N Pods) → legacy now
* **ReplicaSet (RS)** → its replacement → the difference is **how it selects Pods**

```yaml
apiVersion: v1                  # core group
kind: ReplicationController
metadata:
  name: web-rc
spec:
  replicas: 3
  selector:                     # plain key: value → exact match only
    app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: nginx
        image: nginx
```

| | ReplicationController | ReplicaSet |
|---|---|---|
| apiVersion | `v1` (core) | `apps/v1` |
| Selector | Equality-based only | Equality-based **and** set-based |
| Selector required? | No (defaults to template labels) | Yes |
| Used by Deployments? | No | Yes |
| Updates | Manual | Manual (Deployment automates them) |
| Today | Legacy, old tutorials and exam questions | Everywhere, but created by Deployments |

* `kubectl create rc` no longer exists → RCs only via YAML
* In practice → `kubectl get rc` is empty on real clusters | `kubectl get rs` shows dozens, all owned by Deployments

## Selectors: equality-based vs set-based

* **Label** = name tag on an object → `app: web`
* **Selector** = filter that finds objects by their labels
* Analogy → a team of 5 engineers tagged "Kubernetes", "Automation", "CI/CD" → selector "all Kubernetes experts" finds 2 of them without knowing their names
* Used by ReplicaSets, Deployments, StatefulSets, DaemonSets, Services, Jobs, NetworkPolicies → labels and selectors are everywhere

### Equality-based

* Exact match → `app = web`, `env != prod`

```yaml
selector:
  matchLabels:
    app: web
```

### Set-based

* Rules instead of exact values → `app in (web, api)`, "not prod", "has a tier label"

| Operator | Matches when | Example |
|---|---|---|
| `In` | value is one of the list | `app` is `nginx` or `apache` |
| `NotIn` | value is none of the list | `env` is not `development` |
| `Exists` | key is present (any value) | Pod has a `tier` label |
| `DoesNotExist` | key is absent | Pod has no `debug` label |

```yaml
apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: web-setbased
spec:
  replicas: 3
  selector:
    matchExpressions:
      - key: app
        operator: In
        values: ["nginx", "apache"]
      - key: env
        operator: NotIn
        values: ["development"]
      - key: tier
        operator: Exists          # no values list for Exists / DoesNotExist
      - key: debug
        operator: DoesNotExist
  template:
    metadata:
      labels:                     # must satisfy every rule above
        app: nginx
        env: production
        tier: frontend            # no debug label, or the selector fails
    spec:
      containers:
      - name: nginx
        image: nginx
```

* Between rules → **AND** | inside one `In` list → **OR**
* `matchLabels` and `matchExpressions` can be combined → still AND
* Template labels must satisfy the selector → otherwise the API server rejects the manifest

| Pod labels | Match? | Why |
|---|---|---|
| `app=nginx, env=production, tier=frontend` | Yes | passes all rules |
| `app=apache, env=staging, tier=backend` | Yes | apache in list, not development, tier present |
| `app=nginx, env=development, tier=frontend` | No | env is development |
| `app=nginx, env=production` | No | no tier label |
| `app=nginx, env=production, tier=frontend, debug=true` | No | debug label present |

* Same syntax on the command line → test a selector before writing it:

```bash
kubectl get pods -l app=web                                   # equality
kubectl get pods -l 'env!=prod'
kubectl get pods -l 'app in (nginx,apache)'                   # In
kubectl get pods -l 'env notin (development)'                 # NotIn
kubectl get pods -l tier                                      # Exists
kubectl get pods -l '!debug'                                  # DoesNotExist
kubectl get pods -l 'app in (nginx,apache),tier,!debug'       # comma = AND
```

* In practice → most manifests use plain `matchLabels` → set-based is for "one of these", "not that", "has this key"

## Deployment

* A manager for Pods → I declare what I want, it keeps making it true
* Gives:
    * **Replicas** → always keep N Pods | one dies → a new one appears
    * **Rolling updates** → change the image → Pods replaced gradually, no downtime
    * **Rollbacks** → new version broken → undo it
    * **Scaling** → 3 → 10 Pods with one command

### The three layers

```
Deployment  →  ReplicaSet  →  Pods  →  Containers
(versions)     (count)        (run)     (the app)
```

* Deployment wraps ReplicaSets → handles versions, rolling updates, rollback
* ReplicaSet wraps Pods → keeps the count
* Pod wraps containers → shares network and storage
* On an update → Deployment creates a **new ReplicaSet** for the new version, scales it up, scales the old one down
* Old ReplicaSet stays (at 0 Pods) → that is what makes rollback instant
* I never create ReplicaSets myself → the Deployment does it
* Pod names show this → `web-7d4b9c8f6-x2kqp` = Deployment `web` + ReplicaSet hash `7d4b9c8f6` + random Pod suffix

### Why rolling updates are safe

* New Pods must be **Ready** before old Pods are removed
* New image broken (e.g. wrong tag) → new Pods stuck in `ImagePullBackOff` → old Pods keep serving → no downtime
* Then `kubectl rollout undo` brings the old version back

### Deployment manifest and update strategy

* Same shape as a ReplicaSet → only `kind` changes, plus an optional `strategy`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  annotations:
    kubernetes.io/change-cause: "initial release nginx 1.19"
spec:
  replicas: 3
  revisionHistoryLimit: 10     # old ReplicaSets kept for rollback (default 10)
  selector:
    matchLabels:
      app: web
  strategy:
    type: RollingUpdate        # default
    rollingUpdate:
      maxSurge: 1              # at most 1 Pod above replicas during an update
      maxUnavailable: 0        # never drop below 3 Ready Pods
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: nginx
        image: nginx:1.19      # pin a tag so updates are visible
```

| Strategy | How | Downtime | Use when |
|---|---|---|---|
| `RollingUpdate` | replace Pods gradually | No | default, most stateless apps |
| `Recreate` | kill all old Pods, then start new ones | Yes | two versions must never run at once |

* `maxSurge` → how many extra Pods allowed during the update (default 25%) → speed
* `maxUnavailable` → how many Pods may be not-Ready during the update (default 25%) → safety
* `maxSurge: 1, maxUnavailable: 0` → slowest but always full capacity

### Labels vs annotations

* **Label** → name tag → used by selectors to find and group objects
* **Annotation** → sticky note → extra information for humans or tools → **never used for selecting**

| | Labels | Annotations |
|---|---|---|
| Purpose | Identify and select | Describe |
| Used by selectors | Yes | No |
| Content | Short key-values (`app: web`) | Anything: change notes, build info, URLs, tool config |
| Example | `env: prod` | `kubernetes.io/change-cause: "update to 1.20"` |

* Common real use → **config for controllers** → e.g. `alb.ingress.kubernetes.io/scheme: internet-facing` is ignored by Kubernetes but read by the AWS Load Balancer Controller
* Annotation values are always strings → quote numbers (`'15'`)

### change-cause → readable rollout history

* `kubernetes.io/change-cause` → shown in the CHANGE-CAUSE column of `rollout history`
* Without it → every revision shows `<none>` → no idea which revision was which
* Set it in the YAML (best) or with `kubectl annotate` **after** each change → the note attaches to whichever revision is current at that moment
* Second annotation onwards needs `--overwrite`
* `--record` used to do this automatically → deprecated

```bash
kubectl set image deploy/web nginx=nginx:1.20
kubectl annotate deploy web kubernetes.io/change-cause="update nginx 1.19 to 1.20" --overwrite
kubectl rollout history deploy/web
```

```
REVISION  CHANGE-CAUSE
1         initial release nginx 1.19
2         update nginx 1.19 to 1.20
```

### Rollback in detail

* `kubectl rollout undo deploy/web` → go to the **previous** revision → run it twice = flip between the same two versions
* `kubectl rollout undo deploy/web --to-revision=N` → jump to any revision still in history
* `kubectl rollout history deploy/web --revision=N` → see that revision's image and settings before jumping
* Rollback is **not** a restore → it creates a **new revision** with the old settings → the old number disappears from the list
    * history 1, 2, 3 → `undo --to-revision=1` → history becomes 2, 3, 4 (4 = the old revision 1)
* Under the hood → current ReplicaSet scaled to 0, the target revision's ReplicaSet scaled back up → no new image pull needed
* History is limited → `revisionHistoryLimit` (default 10) → older ReplicaSets are deleted and can't be rolled back to
* Can always move again → undo the undo, jump to another revision, or `set image` to a brand-new version

### Imperative rollback vs Git

* `rollout undo` changes the live Deployment but not my YAML or its `last-applied-configuration` → warning: "previously managed with 'kubectl apply'…"
* After any imperative change → update the YAML to match → `kubectl apply -f` again → file and cluster agree
* In real teams → rollback = revert the change in Git → CI/CD or Argo CD applies it → `rollout undo` is for emergencies and labs

### Pause and resume

* `kubectl rollout pause deploy/web` → stop rolling out while I make several changes (image, resources, env)
* `kubectl rollout resume deploy/web` → all queued changes go out as **one** rollout, one revision
* Also useful → pause a rollout that looks wrong, investigate, then resume or undo

| | Pod | ReplicaSet | Deployment |
|---|---|---|---|
| Job | Run containers | Keep N Pods | Manage versions of ReplicaSets |
| Self-healing | No | Yes | Yes (via ReplicaSet) |
| Scaling | No | Yes | Yes |
| Rolling update / rollback | No | No | Yes |
| Use directly in production? | Rarely | No | Yes, for stateless apps |

## Commands

```bash
# bare Pod: dies and stays dead
kubectl run solo --image=nginx
kubectl delete pod solo
kubectl get pods                      # gone

# Deployment: comes back
kubectl create deployment web --image=nginx --replicas=3
kubectl get deploy,rs,pods
kubectl delete pod <one-web-pod>
kubectl get pods                      # replaced, new name
kubectl get pods -o wide              # NODE column = which machine each Pod is on

# scale
kubectl scale deployment web --replicas=5

# rolling update + rollback
kubectl set image deployment/web nginx=nginx:1.27   # nginx = the CONTAINER name, not the Deployment name
kubectl rollout status deployment/web
kubectl get rs                        # old RS at 0, new RS at 3
kubectl annotate deploy web kubernetes.io/change-cause="update to 1.27" --overwrite
kubectl rollout history deployment/web
kubectl rollout history deployment/web --revision=2
kubectl rollout undo deployment/web                  # previous revision
kubectl rollout undo deployment/web --to-revision=1  # specific revision

# find the container name for set image
kubectl get deploy web -o jsonpath='{.spec.template.spec.containers[*].name}{"\n"}'

# image currently running
kubectl get deploy -o wide             # CONTAINERS + IMAGES columns

# pause, batch changes, resume
kubectl rollout pause deployment/web
kubectl set image deployment/web nginx=nginx:1.27
kubectl set resources deployment/web -c nginx --limits=memory=256Mi
kubectl rollout resume deployment/web

# not ready yet? (READY 0/3)
kubectl get pods                       # ContainerCreating = still pulling | ImagePullBackOff = bad image
kubectl describe pod <pod>             # Events → exact reason
kubectl get pods -w                    # watch live

# legacy
kubectl get rc
kubectl scale rc web-rc --replicas=4

# break it on purpose
kubectl set image deployment/web nginx=nginx:doesnotexist
kubectl get pods                      # new Pods ImagePullBackOff, old Pods still Running
kubectl rollout undo deployment/web

# labels
kubectl get pods --show-labels
kubectl get pods -l app=web
```

* Node failure → `docker stop <kind-worker>` → node `NotReady` after ~40s → after a few minutes its Pods are recreated on another node → `docker start` to bring it back

!!! tip "Quick revision"

    * Node = machine, Pod = app instance on it
    * Pod = one or more containers sharing one IP (network namespace) and volumes
    * ReplicaSet = keeps N Pods, finds them by label, can't update
    * Deployment = manages ReplicaSets, one per version → rolling updates and rollbacks
    * ReplicationController = legacy RS, equality selectors only → RS adds set-based (`In`, `NotIn`, `Exists`, `DoesNotExist`)
    * `RollingUpdate` (default, no downtime) vs `Recreate` → tune with `maxSurge` / `maxUnavailable`
    * Labels select, annotations describe → `kubernetes.io/change-cause` fills `rollout history`
    * Rollback = new revision with old settings → limited by `revisionHistoryLimit` (10)

!!! question "Interview points"

    * Node vs Pod? → a node is a worker machine that provides compute; a Pod is the smallest deployable unit, one or more containers, scheduled onto a node
    * What is a Pod? → the smallest deployable unit in Kubernetes: one or more containers sharing a network namespace (one IP) and volumes
    * How do containers in the same Pod talk? → over localhost, because they share the Pod's network namespace
    * What is the pause container? → a tiny container that holds the Pod's network namespace open so app containers can join it
    * What happens if a bare Pod dies? → nothing recreates it; only controllers like ReplicaSets bring Pods back
    * How does a ReplicaSet know which Pods are its own? → by label selector, not by name or owner
    * You create a Pod with the same labels as a ReplicaSet's Pods, what happens? → the ReplicaSet counts it and deletes one Pod to get back to the desired count
    * Why use a Deployment instead of a ReplicaSet? → a ReplicaSet can't do rolling updates; a Deployment creates a new ReplicaSet per version and shifts Pods gradually, which also enables rollback
    * How does a rollback work? → the old ReplicaSet is kept at 0 replicas; rollback scales it back up and scales the new one down
    * New image tag doesn't exist, does the app go down? → no, new Pods fail with ImagePullBackOff while old Pods keep running, because old Pods are only removed once new ones are Ready
    * ReplicationController vs ReplicaSet? → same job; RC is legacy core v1 with equality-based selectors only, RS is apps/v1 and also supports set-based selectors, and is what Deployments use
    * Equality-based vs set-based selectors? → equality matches exact values (=, !=); set-based uses In, NotIn, Exists and DoesNotExist; rules are ANDed
    * Can a cluster run many ReplicaSets? → yes; names must be unique per namespace and selectors shouldn't overlap or they fight over Pods
    * You change the image in a bare ReplicaSet, what happens? → existing Pods keep the old image; only Pods created later use the new one
    * RollingUpdate vs Recreate? → RollingUpdate replaces Pods gradually without downtime; Recreate deletes all old Pods first, used when two versions can't run together
    * What do maxSurge and maxUnavailable control? → maxSurge is how many extra Pods may exist during an update, maxUnavailable is how many may be unavailable; both default to 25%
    * Labels vs annotations? → labels identify objects and are used by selectors; annotations hold non-identifying metadata for humans and tools and are never used for selection
    * How do you record why a revision was made? → set the kubernetes.io/change-cause annotation, shown in kubectl rollout history
    * Does a rollback restore the old revision number? → no, it creates a new revision with the old template; the old number disappears from history
    * How far back can you roll back? → as far as revisionHistoryLimit allows, 10 old ReplicaSets by default
    * Why pause a Deployment? → to batch several changes into one rollout, or to stop a rollout while investigating a problem
    * Why does kubectl warn after rollout undo? → the live object changed but last-applied-configuration didn't, so the next kubectl apply may behave unexpectedly; update the YAML and re-apply
