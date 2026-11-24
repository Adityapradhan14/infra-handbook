# Manual Scheduling & Static Pods

## Normal scheduling (recap)

```
kubectl apply → API server stores the Pod (nodeName empty)
             → scheduler filters + scores nodes (resources, taints, affinity)
             → scheduler writes spec.nodeName
             → kubelet on that node sees a Pod assigned to it → starts it
```

* The **scheduler** decides where a Pod goes → the **kubelet** only runs what is assigned to its node
* Two ways to get a Pod onto a node **without** the scheduler choosing → manual scheduling and static Pods

| | Manual scheduling | Static Pods |
|---|---|---|
| Created by | Me, through the API server (`kubectl apply`) | The kubelet, from a file on the node |
| How | `spec.nodeName` set in the manifest | Manifest placed in the kubelet's static Pod folder |
| Needs the API server | Yes | No |
| Scheduler involved | No | No |
| Delete with | `kubectl delete pod` | Remove the manifest file from the node |
| Used for | Testing, debugging, scheduler down | Control-plane components, per-node agents |

## Manual scheduling

### What it is

* Set `nodeName` myself → the Pod is already bound to a node → the scheduler never picks it up
* Analogy → a hotel guest who arrives with a room key → the receptionist (scheduler) does nothing → the room staff (kubelet) let them in

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx-manual
spec:
  nodeName: my-new-cluster-worker
  containers:
  - name: nginx
    image: nginx
    ports:
    - containerPort: 80
```

```bash
kubectl apply -f manual-pod.yaml
kubectl get po -o wide        # NODE column = exactly the node I wrote
```

### Why it's useful

* **Debugging** → put a Pod on one specific node to test that node (networking, disk, a bad kubelet)
* **Node-specific test** → check a workload on a node with special hardware
* **Scheduler down** → Pods with `nodeName` still start, because only the kubelet is needed after the API server stores them
* For real workloads → use `nodeSelector` / affinity instead → they go **through** the scheduler, so resources and taints are still checked

### What the scheduler would have checked, and nobody checks now

* **Taints** (`NoSchedule`) → ignored → a Pod with `nodeName` runs even on a tainted node
* **Resources** → not pre-checked → the kubelet checks on admission → not enough CPU/memory → Pod goes `Failed` with reason `OutOfcpu` / `OutOfmemory` instead of waiting in `Pending`
* **Affinity, spreading** → ignored
* **`NoExecute` taints still apply** → they're enforced after the Pod is running (by the node lifecycle controller), so a `nodeName` Pod on a `NoExecute` node gets evicted

### Node that doesn't exist

* `nodeName: no-such-node` → the API server accepts it (no check) → no kubelet ever claims it → Pod stays `Pending`
* The Pod garbage collector deletes Pods bound to nodes that don't exist → the Pod disappears shortly after

### Running a Pod on the control plane

```yaml
spec:
  nodeName: my-new-cluster-control-plane
```

* It runs, even though the control plane carries the taint `node-role.kubernetes.io/control-plane:NoSchedule`

```bash
kubectl describe node my-new-cluster-control-plane | grep -i taint
# Taints: node-role.kubernetes.io/control-plane:NoSchedule
```

* Why → **only the scheduler reads `NoSchedule`** → `nodeName` skips the scheduler → nobody checks the taint
* Proof → same Pod with `nodeSelector: {kubernetes.io/hostname: my-new-cluster-control-plane}` instead of `nodeName` → stays `Pending` → Events: `untolerated taint {node-role.kubernetes.io/control-plane: }`
* Proper way onto the control plane → a toleration for that taint (see [Taints & Tolerations](taints-and-tolerations.md))
* Single-node kind / minikube → the one node has **no** taint, so anything schedules there → a multi-node kind cluster **does** taint the control plane

## The control plane is a node too

* Architecture diagrams draw the control plane as a separate box → on kubeadm / kind it's a normal node that also runs the control-plane components
* Every node, control plane included, has:
    * **kubelet** → runs Pods
    * **container runtime** → containerd
    * **kube-proxy** → Service rules
* The control-plane node additionally runs API server, etcd, scheduler, controller-manager → **as Pods**

```bash
kubectl get po -n kube-system -o wide
# etcd-my-new-cluster-control-plane                      ... my-new-cluster-control-plane
# kube-apiserver-my-new-cluster-control-plane            ... my-new-cluster-control-plane
# kube-controller-manager-my-new-cluster-control-plane   ... my-new-cluster-control-plane
# kube-scheduler-my-new-cluster-control-plane            ... my-new-cluster-control-plane
```

* The taint exists to **protect** it → a heavy app eating CPU/memory there could slow or crash the API server or etcd → whole cluster suffers
* So it's a policy, not a technical limit → that's why `nodeName` gets around it

| Setup | Pods on the control plane? |
|---|---|
| kind / kubeadm, multi-node | Possible → tainted by default |
| Single-node kind / minikube | Yes → no taint |
| EKS / GKE / AKS | No → the provider runs the control plane; it isn't even in `kubectl get nodes` |

## Static Pods

### The chicken-and-egg problem

* Normal Pods need the API server (to be stored) and the scheduler (to be placed)
* But the API server and scheduler **are themselves Pods** → who starts them before they exist?
* Answer → the **kubelet** starts them directly from files on disk → **static Pods**

### What a static Pod is

* A Pod **created and managed by the kubelet** of one node, from a manifest in a folder on that node
* The kubelet watches the folder:
    * file added → start the Pod
    * file changed → recreate the Pod
    * file removed → stop the Pod
* No API server, no scheduler, no controller involved → always bound to that one node
* Can be on **any** node → control plane or worker

### Where the folder is

* Set in the kubelet config → `staticPodPath` → kubeadm / kind default `/etc/kubernetes/manifests`

```bash
# kind nodes are Docker containers → get in with docker exec
docker exec -it my-new-cluster-control-plane bash
grep staticPodPath /var/lib/kubelet/config.yaml     # staticPodPath: /etc/kubernetes/manifests
ls /etc/kubernetes/manifests
# etcd.yaml  kube-apiserver.yaml  kube-controller-manager.yaml  kube-scheduler.yaml
```

* On a real cluster (VMs / bare metal) → `ssh` into the node instead of `docker exec`
* Workers have the same folder → usually empty

### Mirror Pods

* The kubelet also creates a **mirror Pod** in the API server for every static Pod → so `kubectl get pods` can show it
* Name → `<pod-name>-<node-name>` → `nginx-static-pod-my-new-cluster-control-plane`
* The mirror is a **read-only reflection** → I can't really control the static Pod through it
* `kubectl delete pod` on a mirror → the mirror goes away → the kubelet recreates it immediately → the real Pod never stopped
* Only way to remove a static Pod → delete (or move out) its manifest file

### Limits of static Pods

* No Deployment / ReplicaSet → no rolling updates, no replicas, no self-healing across nodes → just the kubelet restarting it on this node
* The spec can't reference other API objects → no ServiceAccount, ConfigMap or Secret
* Node dies → its static Pods die with it → nothing moves them

### Static Pods vs DaemonSets

| | Static Pod | DaemonSet |
|---|---|---|
| Managed by | kubelet, from a local file | DaemonSet controller, through the API server |
| Needs the API server | No | Yes |
| Update with | Editing the file on each node | `kubectl apply` once |
| Typical use | Control-plane components | Per-node agents → log shippers, monitoring, CNI |

### Use cases

* **Control-plane bootstrapping** → API server, etcd, scheduler, controller-manager on kubeadm / kind
* **Must run even if the API server is down** → the kubelet keeps them alive regardless
* Fixing a broken control plane → edit `/etc/kubernetes/manifests/kube-apiserver.yaml` → kubelet restarts the API server with the new config → a common CKA task

## Lab: manual scheduling

```bash
kubectl get nodes

# worker
kubectl apply -f manual-pod.yaml                 # nodeName: my-new-cluster-worker
kubectl get po -o wide

# control plane
# copy the file, change name to nginx-manual-cp and nodeName to my-new-cluster-control-plane
kubectl apply -f manual-pod-cp.yaml
kubectl get po -o custom-columns=POD:.metadata.name,NODE:.spec.nodeName

# proof that the scheduler would refuse → stays Pending
kubectl run sel-cp --image=nginx \
  --overrides='{"apiVersion":"v1","spec":{"nodeSelector":{"kubernetes.io/hostname":"my-new-cluster-control-plane"}}}'
kubectl describe po sel-cp | tail -5

kubectl delete po nginx-manual nginx-manual-cp sel-cp
```

* `kubectl get po -o yaml | grep node` also shows `node.kubernetes.io/not-ready` and `unreachable` → those are tolerations added to every Pod automatically, not related to manual scheduling

## Lab: static Pod

```bash
docker exec -it my-new-cluster-control-plane bash

cat <<EOF > /etc/kubernetes/manifests/static-pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx-static-pod
spec:
  containers:
  - name: nginx
    image: nginx
    ports:
    - containerPort: 80
EOF
exit

kubectl get po                                                  # nginx-static-pod-my-new-cluster-control-plane
kubectl delete po nginx-static-pod-my-new-cluster-control-plane
kubectl get po                                                  # back again

docker exec my-new-cluster-control-plane rm /etc/kubernetes/manifests/static-pod.yaml
kubectl get po                                                  # gone
```

* Never leave a stray or temporary file in `/etc/kubernetes/manifests` → the kubelet treats every manifest there as a Pod to run
* Editing control-plane manifests → keep a backup **outside** that folder (`cp kube-apiserver.yaml /root/`) → a copy left inside becomes a second API server

!!! tip "Quick revision"

    * Scheduler decides the node → writes `nodeName` | kubelet only runs Pods assigned to its node
    * Manual scheduling = I set `nodeName` → scheduler skipped → `NoSchedule` taints, affinity and resource fit not checked
    * Not enough resources on a `nodeName` Pod → kubelet rejects it → `OutOfcpu` / `OutOfmemory`, not `Pending`
    * `NoExecute` still evicts `nodeName` Pods → enforced after scheduling
    * Control plane = a node with kubelet, containerd, kube-proxy + control-plane Pods → protected by the `control-plane:NoSchedule` taint
    * Static Pod = kubelet runs it from a file in `staticPodPath` (`/etc/kubernetes/manifests`) → no API server needed
    * Mirror Pod = read-only copy in the API server, named `<pod>-<node>` → `kubectl delete` doesn't stop the real Pod
    * Remove a static Pod → delete its manifest file

!!! question "Interview points"

    * What is manual scheduling? → setting spec.nodeName in the Pod manifest so the Pod is bound to a node directly and the scheduler is skipped
    * Why can a Pod with nodeName run on a tainted control-plane node? → NoSchedule taints are enforced by the scheduler, and nodeName bypasses the scheduler; the kubelet doesn't check them
    * Does nodeName bypass NoExecute taints? → no, NoExecute is enforced after the Pod is running and the Pod gets evicted
    * What happens if nodeName points to a node without enough resources? → the kubelet rejects the Pod on admission and it fails with OutOfcpu or OutOfmemory
    * What happens if nodeName points to a node that doesn't exist? → the Pod stays Pending because no kubelet claims it, and the Pod garbage collector deletes it
    * What is the proper way to run a Pod on a specific node? → nodeSelector or node affinity, plus a toleration if the node is tainted, so the scheduler still checks the rules
    * How do control-plane components run on a kubeadm cluster? → as static Pods from manifests in /etc/kubernetes/manifests on the control-plane node
    * What is a static Pod? → a Pod managed directly by the kubelet of one node from a local manifest file, without the API server or scheduler
    * How do you find the static Pod directory? → the staticPodPath field in the kubelet config, usually /var/lib/kubelet/config.yaml
    * What is a mirror Pod? → a read-only object the kubelet creates in the API server so a static Pod shows in kubectl, named pod-name dash node-name
    * Why does kubectl delete not remove a static Pod? → it only deletes the mirror Pod; the kubelet still has the manifest and recreates it
    * How do you delete a static Pod? → remove its manifest file from the static Pod directory on that node
    * Static Pod vs DaemonSet? → a static Pod is managed by one node's kubelet from a file and needs no API server; a DaemonSet is managed by a controller through the API server and runs one Pod per node
    * Can you use static Pods on EKS or GKE control planes? → no, the provider manages the control plane and you have no access to its nodes
