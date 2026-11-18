# Container Runtime Internals

*Hands-on notes, how a Pod actually becomes a process on a node*

## The chain, top to bottom

```
kubectl
  ↓
kube-apiserver
  ↓
kubelet (on the node)
  ↓  gRPC via CRI
containerd      ← high-level runtime: images, lifecycle
  ↓
runc            ← low-level runtime: creates the container, exits
  ↓
Linux kernel    ← namespaces + cgroups do the real isolation
```

* With plain Docker → `docker` → `dockerd` → `containerd` → `runc` → same bottom half
* Restaurant analogy → kubelet = waiter taking orders from the API server | containerd = kitchen manager, gets ingredients ready (pulls and unpacks images) | runc = cook, makes the dish (starts the container) and leaves | `containerd-shim` = helper who stays by the dish and watches it

## A container is just a process

* Linux has no "container" object
* Container = **normal Linux process** + **namespaces** (what it can see) + **cgroups** (how much it can use) + **its own root filesystem** (the image)
* runc sets these up, starts the process, done

## Linux namespaces: what a process can see

* Give a process its own private view of the system → it thinks it's alone on the machine
* Analogy → office building with many companies → each floor has its own room numbers and reception board → floor 3 can't see floor 5 → but one building, one foundation = **one shared kernel**

| Namespace | Isolates | What the container sees |
|---|---|---|
| PID | Process IDs | Its own process list, its main process is PID 1 |
| NET | Network | Its own interfaces, IP, ports, routing table |
| MNT | Mount points | Its own filesystem (the image), not the host's |
| UTS | Hostname | Its own hostname |
| IPC | Shared memory, message queues | Can't touch other processes' shared memory |
| USER | User IDs | Can be root inside, a normal user outside |
| CGROUP | cgroup view | Only its own cgroup tree |
| TIME | System clocks (newer) | Can have its own clock offset |

* Big three for interviews → **PID, NET, MNT**
* Kubernetes angle:
    * each container → own PID and MNT namespace
    * all containers in a Pod → **share one NET namespace** (held by the pause container) → one IP, talk over `localhost`
    * `kubectl exec` / `docker exec` → **enter** an existing container's namespaces (`setns` syscall)
* Weak spot → all containers share the host kernel → a kernel exploit can escape the namespace → why gVisor and Kata Containers (microVMs) exist
* More detail and labs → Docker's [Namespaces](../docker/namespaces.md) chapter

```bash
sudo unshare --pid --fork --mount-proc bash    # own PID namespace
ps aux                                         # only 2 processes, bash is PID 1
exit
sudo unshare --uts bash                        # own hostname
hostname container-test && hostname
exit
ls -l /proc/$$/ns                              # my shell's namespaces
lsns                                           # all namespaces on the system
```

## cgroups: how much a process can use

* **Control groups** → Linux kernel feature that **limits and measures** resources for a group of processes
* Namespaces = what you **see** | cgroups = what you **use**
* Analogy → hostel warden: "room 4 gets at most 2 units of power" → take more → throttled or cut off

| Resource | At the limit |
|---|---|
| CPU | **Throttled** (slowed down), not killed |
| Memory | **Killed** by the OOM killer → `OOMKilled`, exit code `137` |
| Disk I/O | Reads/writes slowed |
| PIDs | Can't create more processes (stops fork bombs) |

* Also **measures** usage → that is where `docker stats` and `kubectl top` get numbers, and what autoscaling reads

### Requests and limits in Kubernetes

```yaml
resources:
  requests:            # used by the SCHEDULER to pick a node
    cpu: "250m"        # 250 millicores = 1/4 CPU
    memory: "128Mi"
  limits:              # enforced by CGROUPS on the node
    cpu: "500m"
    memory: "256Mi"
```

* **requests** → "find a node with at least this much free" → scheduling decision
* **limits** → hard ceiling → runc writes them into the container's cgroup
* Over CPU limit → throttled (slow, alive) | over memory limit → `OOMKilled` (shown in `kubectl describe pod`)
* CPU throttled vs memory killed → very common interview question

### cgroup v1 vs v2

* v1 → older, separate tree per resource, messy
* v2 → one unified tree, better memory handling → modern default (Ubuntu 22.04+)
* Recent Kubernetes (1.35+) refuses to run on cgroup v1 by default

```bash
stat -fc %T /sys/fs/cgroup        # cgroup2fs = v2
cat /proc/self/cgroup             # which cgroup my shell is in
systemd-cgls                      # tree of all cgroups
docker run --rm -m 50m polinux/stress stress --vm 1 --vm-bytes 100M
echo $?                           # 137 = killed (128 + signal 9)
```

## runc: the low-level runtime

* Small program that **actually creates and starts** a container
* Reference implementation of the **OCI runtime spec** (Open Container Initiative = the standard for how to run a container)
* Gets a ready folder (root filesystem) + `config.json` → creates namespaces → applies cgroups → sets the root filesystem → starts the process → **exits**
* Does not pull images, does not do networking, does not stay running
* Because it follows a standard, it can be swapped:
    * `crun` → written in C, faster and lighter
    * gVisor (`runsc`) → sandboxed user-space kernel, stronger isolation
    * Kata Containers → each container inside a tiny VM

## containerd: the high-level runtime

* The container manager running on every node, always on (a daemon)
* Jobs:
    * pulls images from registries (Docker Hub, ECR)
    * stores images and unpacks layers into a filesystem (**snapshotters**, usually overlayfs)
    * prepares the container config, then **calls runc**
    * manages lifecycle → create, start, stop, delete, status
    * talks to the kubelet through **CRI** (gRPC)
    * starts one `containerd-shim` per container → keeps containers alive even if containerd restarts, holds stdout/stderr, records exit codes
* Restarting crashed containers → that is the **kubelet's** job (restart policy), not containerd's
* Came out of Docker in 2017, donated to CNCF → now the standard node runtime

## containerd vs runc

| | containerd | runc |
|---|---|---|
| Level | High-level runtime | Low-level runtime |
| Job | Images, lifecycle, talks to the kubelet | Creates one container with namespaces + cgroups |
| Runs how long | Always (daemon) | A split second, then exits |
| Talks to | kubelet above (CRI), runc below | Linux kernel |
| Knows about images? | Yes, pulls, unpacks, stores | No, only gets a ready folder + config |
| Standard | Implements **CRI** | Implements **OCI runtime spec** |
| Swappable with | CRI-O | crun, gVisor, Kata |

* One line → containerd prepares and manages, runc creates and exits

## containerd vs Docker, and the dockershim story

* Docker → full developer tool: CLI, `docker build`, Compose, networks, volumes
* containerd → only the runtime part, pulled out of Docker
* Kubernetes talks to runtimes only through **CRI** → Docker never spoke CRI → Kubernetes kept an adapter called **dockershim**
* **Kubernetes 1.24 (2022) removed dockershim** → nodes now use containerd or CRI-O directly
* Docker-built images still work everywhere → they are standard OCI images
* Only Docker as the **node runtime** was dropped, not Docker as a build tool

## Tools to look inside a node

| Tool | For |
|---|---|
| `crictl` | Talks CRI, shows what the kubelet sees → use this on Kubernetes nodes |
| `ctr` | containerd's own low-level CLI, for debugging |
| `nerdctl` | Docker-like CLI for containerd |

```bash
docker exec -it my-first-cluster-control-plane bash
crictl ps                       # running containers (like docker ps)
crictl pods                     # Pod sandboxes
crictl images
systemctl status containerd
ps aux | grep -E "containerd|shim"
```

* Break it → inside the node `systemctl stop containerd` → existing Pods keep running (shims keep them alive) → new Pods can't start → `systemctl start containerd`

!!! tip "Quick revision"

    * Container = process + namespaces (see) + cgroups (use) + own root filesystem
    * kubelet → CRI → containerd → runc → kernel
    * CPU over limit = throttled, memory over limit = OOMKilled (137)
    * dockershim removed in 1.24; Docker images still work (OCI)

!!! question "Interview points"

    * What is a container, technically? → a normal Linux process isolated with namespaces, limited with cgroups, running on its own root filesystem
    * Namespaces vs cgroups? → namespaces isolate what a process can see; cgroups limit and measure what it can use
    * Which namespace do containers in a Pod share? → the network namespace, held by the pause container, so they share one IP and use localhost
    * Container exceeds its CPU limit vs its memory limit? → CPU gets throttled; memory gets OOMKilled with exit code 137
    * Requests vs limits? → requests are used by the scheduler to place the Pod; limits are enforced on the node through cgroups
    * What is runc? → the low-level OCI runtime that containerd calls to create the container; it sets up namespaces and cgroups, starts the process and exits
    * What is containerd? → a CNCF high-level runtime that pulls and stores images, manages container lifecycle and calls runc; Kubernetes talks to it over CRI
    * Why did Kubernetes drop Docker? → Docker doesn't implement CRI, so Kubernetes needed the dockershim adapter; it was removed in 1.24 in favour of containerd and CRI-O
    * Do Docker-built images still work on Kubernetes? → yes, they are OCI images
    * What keeps a container running if containerd restarts? → the containerd-shim, which is the container's parent process
    * Why are containers weaker isolation than VMs? → they share the host kernel, so a kernel exploit can escape; gVisor and Kata add a stronger boundary
