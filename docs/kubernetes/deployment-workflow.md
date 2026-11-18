# From kubectl apply to Running Pod

## The short version

* `kubectl apply -f deployment.yaml` sets off a chain → no component does everything, each one does one small job and writes the result back to the API server
* The next component **watches** the API server, sees the change, does its job → like a relay race where the baton is always handed through the API server

```
kubectl ─▶ API server ─▶ etcd
                │
   Deployment controller   → creates ReplicaSet
   ReplicaSet controller   → creates Pod objects (no node yet)
   Scheduler               → picks a node, writes nodeName
   kubelet on that node    → containerd pulls image, CNI gives IP, containers start
   kubelet                 → reports status back → Pod Running
```

## Step 1: kubectl

* I run `kubectl apply -f python-frontend-deployment.yaml`
* kubectl checks the YAML → syntax (indentation, format) and basic schema (valid `apiVersion`, `kind`)
* Turns it into a REST request (`POST`/`PATCH`) and sends it to the API server
* See the actual HTTP calls → `kubectl apply -f deployment.yaml -v=8`

## Step 2: API server

1. **Authentication** → who sent this? (my client certificate from the kubeconfig)
2. **Authorization** → RBAC: is this user allowed to create Deployments in this namespace?
3. **Admission** → mutating webhooks may change it, validating webhooks may reject it
4. **Validation** → full schema check
5. **Store in etcd** → the Deployment's desired state (name, replicas, Pod template)
6. **Respond** → `deployment.apps/python-frontend created`
* At this point → **nothing is running yet**, only a record in the database

## Step 3: Deployment controller

* Part of `kube-controller-manager` → watches Deployment objects through the API server
* Sees a new Deployment with no ReplicaSet → asks the API server to create a **ReplicaSet** object → stored in etcd
* Keeps updating the Deployment's status → how many replicas are **ready** (containers running and passing readiness checks) and **available** (ready for at least `minReadySeconds`)

## Step 4: ReplicaSet controller

* Watches ReplicaSets through the API server (never reads etcd directly)
* Sees desired 3, actual 0 → asks the API server to create 3 **Pod objects**
* These Pods are only records in etcd → no node assigned (`nodeName` empty), no containers yet
* Status → `Pending`

## Step 5: Scheduler

* Watches for Pods with an empty `nodeName`
* For each one → filters nodes that can't run it (resources, taints, affinity) → scores the rest → picks the best
* Writes `nodeName` into the Pod object through the API server → stored in etcd
* Scheduler's job ends here → it does not start anything

## Step 6: kubelet on the chosen node

* Every kubelet watches for Pods whose `nodeName` = its own node
* Sees the new Pod → reads its spec (containers, ports, volumes, env)
* Through **CRI** (gRPC) tells `containerd` to:
    * pull the image from the registry
    * create the Pod sandbox (pause container, network namespace) → **CNI** plugin gives it an IP
    * mount volumes (through **CSI** if needed)
    * create and start the containers (`containerd` → `runc`)
* Pod status → `ContainerCreating` → `Running`

## Step 7: Running and kept running

* kubelet keeps checking container health (probes) → restarts crashed containers → reports status to the API server → stored in etcd
* Pod gets deleted or its node dies → **ReplicaSet controller** sees actual 2, desired 3 → creates a new Pod → scheduler places it → kubelet starts it
* Who does what after startup:
    * kubelet → health of containers on its node
    * ReplicaSet controller → recreates missing Pods
    * Deployment controller → manages ReplicaSets (versions), does **not** recreate Pods itself

## Watch it happen

```bash
kubectl create deployment web --image=nginx --replicas=3
kubectl get events --sort-by=.metadata.creationTimestamp
kubectl get deploy,rs,pods -o wide
kubectl describe pod <web-pod>        # Events: Scheduled → Pulling → Pulled → Created → Started
```

* `kubectl describe pod` → Events section at the bottom shows each step and which component did it (`default-scheduler`, `kubelet`)
* Best debugging habit → stuck Pod = look at Events first

| Pod stuck in | Usually means | Look at |
|---|---|---|
| `Pending` | Scheduler can't find a node (no resources, taints, affinity) | `kubectl describe pod` → Events |
| `ContainerCreating` | Image pull, volume mount or CNI still in progress or failing | Events, node's kubelet |
| `ImagePullBackOff` / `ErrImagePull` | Wrong image name/tag or no registry access | Image name, registry credentials |
| `CrashLoopBackOff` | Container starts, then exits, again and again | `kubectl logs <pod> --previous` |

!!! tip "Quick revision"

    * kubectl → API server (authn, authz, admission, etcd) → Deployment controller (ReplicaSet) → ReplicaSet controller (Pods) → scheduler (nodeName) → kubelet (containerd, CNI, CSI) → Running
    * Every component only talks to the API server and watches it for changes

!!! question "Interview points"

    * Walk me through what happens on kubectl apply of a Deployment → kubectl sends it to the API server, which authenticates, authorizes, runs admission and stores it in etcd; the Deployment controller creates a ReplicaSet; the ReplicaSet controller creates Pod objects; the scheduler assigns each Pod a node; the kubelet on that node asks containerd to pull the image and start the containers, CNI gives the Pod an IP, and the kubelet reports status back
    * When kubectl says "deployment created", is anything running? → no, only the object is stored in etcd; controllers, the scheduler and the kubelet do the rest asynchronously
    * Who recreates a deleted Pod, the Deployment or the ReplicaSet? → the ReplicaSet controller; the Deployment controller manages ReplicaSets
    * Do controllers read etcd directly? → no, everything goes through the API server, which is the only component talking to etcd
    * A Pod is stuck in Pending, what do you check? → kubectl describe pod and its Events, usually the scheduler couldn't find a node because of resources, taints or affinity
    * CrashLoopBackOff, what do you check? → kubectl logs --previous for the crashed container, then the command, config and probes
