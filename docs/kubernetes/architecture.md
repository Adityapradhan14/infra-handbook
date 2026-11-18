# Architecture

## The big picture

* A Kubernetes **cluster** = a group of machines (nodes) working as one
* Two kinds of nodes:
    * **Control plane** → the brain → decides what runs, where, and what is allowed
    * **Worker nodes** → the muscles → actually run my app containers
* Every node runs Linux, containerd and the kubelet | only the control plane runs the "brain" components

```
                       ┌──────────────── CONTROL PLANE ────────────────┐
  kubectl ───────────▶ │  kube-apiserver ◀──▶ etcd                     │
                       │       ▲   ▲   ▲                               │
                       │       │   │   └── kube-controller-manager     │
                       │       │   └────── kube-scheduler              │
                       │       └────────── cloud-controller-manager    │
                       └───────┬───────────────────────────────────────┘
                               │ (everything talks to the API server)
          ┌────────────────────┴────────────────────┐
  ┌───────▼──────── WORKER NODE 1 ──┐     ┌──────────▼──── WORKER NODE 2 ──┐
  │ kubelet      kube-proxy         │     │ kubelet      kube-proxy        │
  │ containerd → runc               │     │ containerd → runc              │
  │ [ pod ] [ pod ] [ pod ]         │     │ [ pod ] [ pod ]                │
  │ CNI (network)  CSI (storage)    │     │ CNI (network)  CSI (storage)   │
  └─────────────────────────────────┘     └────────────────────────────────┘
```

* Golden rule → **every component talks only to the API server**, never directly to each other or to etcd (except the API server itself)

## Control plane

* The brain of Kubernetes → stores state, validates changes, assigns work to nodes, keeps everything in sync
* Four core components + one optional

### kube-apiserver (the front door)

* Entry point for every request → `kubectl`, controllers, scheduler, kubelets all go through it
* For every request it does, in order:
    1. **Authentication** → who are you? (certificate, token, OIDC)
    2. **Authorization** → are you allowed? (RBAC) → see [RBAC & Request Flow](rbac.md)
    3. **Admission control** → modify (mutating) or approve/reject (validating) the object → see [Webhooks, CRDs & Operators](webhooks-crds-operators.md)
    4. **Schema validation** → is the object well-formed?
    5. **Save to etcd**
* Lets others **watch** for changes → when something changes, the scheduler, controllers and kubelets get notified
* Does not run containers or schedule anything → it receives, checks, secures, saves and broadcasts
* Only component that talks to etcd
* Analogy → reception desk + security guard + notice board of a building

### etcd (the database)

* Distributed **key-value store** → holds the entire cluster state (every Deployment, Pod, Secret, ConfigMap)
* Desired state lives here → lose etcd without a backup = lose the cluster
* Usually run as 3 or 5 copies kept in sync by the **Raft** algorithm → see [etcd & Raft](etcd-and-raft.md)

### kube-scheduler (the matchmaker)

* Watches for new Pods that have no node yet (`nodeName` empty)
* Picks the best node based on → free CPU/RAM, node labels, affinity rules, taints and tolerations
* Writes its choice (`nodeName`) into the Pod object through the API server
* Does **not** start the Pod → the kubelet on that node does
* Three stages:
    * **Queue** → Pods wait in a queue, sorted by priority (`QueueSort`); `PreEnqueue` checks a Pod is ready to be considered
    * **Scheduling cycle** → `PreFilter` (basic checks) → `Filter` (remove nodes that can't run it: not enough resources, wrong labels, blocking taints) → `Score` (rank the remaining nodes: balance, spreading, affinity) → `NormalizeScore` → `Reserve` (hold the spot so no other Pod takes it) → `Permit` (can wait for outside approval, e.g. gang scheduling)
    * **Binding cycle** → `PreBind` (last checks, e.g. volumes ready) → `Bind` (write `nodeName` to the Pod) → `PostBind` (cleanup, metrics)
* Analogy → hotel receptionist: filters out full rooms, ranks the rest, reserves one, hands over the key

### kube-controller-manager (the robots)

* One process running many small **controllers** → each watches one kind of object and fixes differences
* This is where reconciliation happens

| Controller | What it keeps true |
|---|---|
| Deployment controller | Right ReplicaSet exists for each version |
| ReplicaSet controller | Right number of Pods running |
| Node controller | Notices dead nodes, evicts their Pods |
| DaemonSet controller | One Pod on every node |
| Job / CronJob controller | Jobs run to completion / on schedule |
| Namespace controller | Deleting a namespace cleans up everything inside it |
| EndpointSlice controller | Service knows the IPs of its healthy Pods |

* Operators add **custom controllers** on top (cert-manager, Argo CD, Prometheus Operator)

### cloud-controller-manager (optional)

* Connects Kubernetes to a cloud provider's API
* Creates a cloud load balancer for `Service type=LoadBalancer`, attaches cloud routes, notices deleted cloud VMs
* Present on managed clusters (EKS, GKE, AKS) | not present on `kind` or bare-metal clusters

## Worker nodes

* The machines that run my containers
* Receive instructions from the control plane (via the API server) → start Pods, attach volumes, set up networking, check health, report status back

### kubelet (the node's manager)

* Agent on every node → watches the API server for Pods assigned to **its** node
* For each Pod → asks the container runtime to pull images and start containers → calls CNI for networking → calls CSI for volumes
* Runs **probes** (liveness, readiness, startup) → restarts crashed containers
* Reports Pod and node status back to the API server
* Does not decide where Pods run (scheduler's job) → only makes sure assigned Pods run correctly
* Only Kubernetes component that is a normal systemd service, not a Pod

### kube-proxy (Service networking)

* Runs on every node → makes **Services** work
* When a Service is created → programs iptables / IPVS / nftables rules on the node → traffic to the Service IP is load-balanced across the Service's ready Pods
* Pod behind a Service dies or is replaced → kube-proxy updates the rules
* It does **not** give Pods their IPs → that is CNI's job
* Some CNIs (e.g. Cilium) can replace kube-proxy completely with eBPF

### Container runtime

* Software that actually runs containers → `containerd` or `CRI-O`
* `containerd` pulls images and manages containers → calls `runc` to create each one → see [Container Runtime Internals](container-runtime.md)
* Docker itself is no longer a node runtime (removed in Kubernetes 1.24)

## The three plug-in interfaces

* Kubernetes does not run containers, network Pods or create disks by itself → it defines standard interfaces and plugins do the work

| Interface | Full name | Job | Examples |
|---|---|---|---|
| CRI | Container Runtime Interface | How the kubelet tells a runtime to pull images and start/stop containers (gRPC) | containerd, CRI-O |
| CNI | Container Network Interface | Gives each Pod an IP, connects Pods across nodes, enforces network policies | Calico, Cilium, Flannel, kindnet |
| CSI | Container Storage Interface | Creates, attaches and mounts volumes from storage systems | AWS EBS, GCP PD, Azure Disk, Ceph, Longhorn |

* Why interfaces → swap the plugin without changing Kubernetes itself

## Control plane vs data plane

| | Control plane | Data plane (workers) |
|---|---|---|
| Job | Manages the cluster | Runs the applications |
| Components | API server, etcd, scheduler, controller manager, CCM | kubelet, kube-proxy, container runtime |
| Location | Dedicated machines, often 3 for high availability | Every worker node |
| If it goes down | Running apps keep running, but no changes possible | Apps on that node stop; Pods get recreated elsewhere |

## How two Pods talk through a Service

* Example → Python frontend Pod needs Redis
1. Frontend connects to `redis-service:6379` → **CoreDNS** turns the name into the Service's ClusterIP
2. Packet leaves the frontend Pod → kube-proxy's rules on that node rewrite the ClusterIP to the IP of one ready Redis Pod (load balancing)
3. **CNI** carries the packet across the cluster network to that Redis Pod, even on another node
4. Redis replies → the reply goes straight back to the frontend Pod over the same connection
* Service = stable name and IP in front of Pods whose IPs keep changing
* kube-proxy picks the Pod | CNI delivers the packet

!!! tip "Quick revision"

    * Control plane = API server (front door), etcd (database), scheduler (picks node), controller manager (reconciles), CCM (cloud)
    * Worker = kubelet (runs Pods on the node), kube-proxy (Service rules), container runtime (containerd)
    * Everything talks to the API server; only the API server talks to etcd
    * CRI = runtime, CNI = network, CSI = storage

!!! question "Interview points"

    * Components of the control plane? → kube-apiserver, etcd, kube-scheduler, kube-controller-manager, and cloud-controller-manager on cloud clusters
    * Components of a worker node? → kubelet, kube-proxy, container runtime (containerd/CRI-O), plus CNI and CSI plugins
    * What does the API server do? → authenticates, authorizes, runs admission, validates and stores objects in etcd, and lets other components watch for changes; it is the only component that talks to etcd
    * Does the scheduler start Pods? → no, it only writes the chosen nodeName into the Pod; the kubelet on that node starts it
    * How does the scheduler pick a node? → filter out nodes that can't run the Pod, score the rest, reserve and bind the best one
    * What happens if the control plane goes down? → running Pods keep running, but nothing can be created, changed or rescheduled until it is back
    * Does kube-proxy assign Pod IPs? → no, the CNI plugin does; kube-proxy programs iptables/IPVS/nftables rules so Service IPs reach healthy Pods
    * Is the kubelet a Pod? → no, it runs as a systemd service on each node
    * CRI vs CNI vs CSI? → CRI is how the kubelet talks to the container runtime, CNI gives Pods networking, CSI gives Pods storage
    * What is the cloud-controller-manager? → the control-plane piece that talks to the cloud provider's API, e.g. creating load balancers for LoadBalancer Services
