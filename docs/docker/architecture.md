# Architecture

*Hands-on notes, Docker architecture*

## Daemon

* Daemon → any program that runs in the background all the time, no window or terminal, waits for work
* Names end in `d` by tradition → `sshd`, `systemd`, `crond`, `dockerd`, `containerd`
* "The Docker daemon" = `dockerd` → same thing

## The components (top to bottom)

* `docker` CLI (`/usr/bin/docker`) → only a client / remote control, does no container work itself
* CLI turns `docker run nginx` into an HTTP request (REST API) → sends it through `/var/run/docker.sock`
* `docker.sock` → Unix socket = special file two programs on the same machine talk through
* `docker --version` works even when the daemon is down → only the client is involved
* Access to `docker.sock` = effectively root access
* `dockerd` → the manager, runs as root → API, image builds (BuildKit), networks (creates `docker0`, iptables NAT, container IPs), volumes, pull/push, logs
* `dockerd` does NOT run containers itself → delegates to `containerd`
* `containerd` → container runtime manager → stores images, unpacks layers (snapshots), container lifecycle (create, start, stop, delete), starts a shim per container
* `containerd` came out of Docker, now an independent CNCF project → package `containerd.io`
* `containerd-shim` → one small process per container = its babysitter → stays as the container's parent, holds stdin/stdout (`docker logs`, `docker attach`), records exit code
* Shim is the parent → dockerd/containerd can restart without killing containers (with `live-restore`)
* `runc` → low-level tool that creates the container → namespaces → cgroups → root filesystem → starts the process → exits
* `runc` does not stay running → after that the container is a normal process (`ps aux | grep nginx` shows it)
* Linux kernel → where isolation actually happens (namespaces, cgroups, OverlayFS, iptables/nftables + veth)
* Registry → online store of images (Docker Hub, GHCR, ECR) → `dockerd` pulls from and pushes to it

| Component | Job | Lifetime |
|---|---|---|
| `dockerd` | Manager: requests, pulls, networks, volumes, logs | Always running |
| `containerd` | Supervisor: images, start/stop containers | Always running |
| `containerd-shim` | Babysitter for one container | As long as its container |
| `runc` | Builder: creates the container | Split second, then exits |

## dockerd vs containerd

* `dockerd` → Docker-specific features: commands, Dockerfiles, `-p` syntax, `docker0`, volumes, logs
* `containerd` → only runs containers, knows nothing about Dockerfiles, Compose or `docker0`
* Why split → core "run containers" part separated so other tools can use it without the rest of Docker
* Kubernetes uses `containerd` directly, no `dockerd`
* `dockerd` is started with `--containerd=/run/containerd/containerd.sock` → that's how it finds `containerd`
* Docker's containers live in containerd's `moby` namespace → `sudo ctr -n moby containers list`

| | Restaurant analogy |
|---|---|
| `docker` CLI | Customer placing an order |
| `docker.sock` | Order window |
| `dockerd` | Manager: takes orders, buys ingredients, arranges tables, keeps records |
| `containerd` | Head chef: only cooks |
| shim + `runc` | Kitchen helpers who plate each dish |
| Kernel | The kitchen itself |
| Registry | Supplier / warehouse |

## What happens on `docker run -d -p 8080:80 nginx`

1. CLI sends a POST request over `docker.sock` to `dockerd`
2. `dockerd` checks for the image locally → missing → pulls the layers from Docker Hub
3. `dockerd` sets up the network (veth pair, IP, iptables rule for 8080) and any volumes
4. `dockerd` asks `containerd` over gRPC to create and start the container
5. `containerd` prepares the filesystem snapshot (layers + fresh writable layer) and starts a shim
6. Shim calls `runc` → creates namespaces and cgroups, sets the root filesystem
7. `runc` starts nginx, then exits
8. nginx runs as an isolated process, shim is its parent, collects its output
9. CLI prints the container ID and gives the terminal back (`-d`)

* `docker run` = pull (if missing) + create + start + attach (unless `-d`)

## Lab: see the stack on my machine

```bash
ps -ef --forest | grep -E 'dockerd|containerd|shim' | grep -v grep
systemctl status docker --no-pager | head -5
systemctl status containerd --no-pager | head -5
docker info | grep -E 'Runtime|Storage Driver|Cgroup'
ls /var/lib/docker
sudo ctr -n moby containers list
```

* Two separate services, two separate processes → `docker` and `containerd`

!!! question "Interview points"

    * What does the docker CLI do? → nothing by itself; it sends REST API requests to dockerd over /var/run/docker.sock
    * Why is access to docker.sock dangerous? → whoever can write to it controls dockerd, which runs as root, so it is effectively root access
    * dockerd vs containerd? → dockerd handles Docker features (API, builds, networks, volumes, logs); containerd only manages images and container lifecycle
    * What does runc do? → creates namespaces and cgroups, sets the root filesystem, starts the process, then exits
    * Why a shim per container? → it stays as the container's parent, keeps its logs and exit code, so dockerd/containerd can restart without killing containers
    * Does Kubernetes need Docker? → no, it talks to containerd directly
    * What is a daemon? → a background program that runs all the time waiting for work, usually named with a trailing d
