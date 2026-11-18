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

### Why I don't use ReplicaSets directly

* A ReplicaSet can keep count but **can't update** → change the image in its template → existing Pods keep the old image, only new Pods get the new one
* That is why a Deployment sits on top of it
* ReplicationController → older version of ReplicaSet, replaced by it (ReplicaSet added richer selectors like `in`, `notin`, `exists`)

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
kubectl set image deployment/web nginx=nginx:1.27
kubectl rollout status deployment/web
kubectl get rs                        # old RS at 0, new RS at 3
kubectl rollout history deployment/web
kubectl rollout undo deployment/web

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
