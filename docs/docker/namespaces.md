# Namespaces

*Hands-on notes, plus Red Hat's "The 7 most used Linux namespaces" article*

## What a namespace is

* Kernel feature that partitions resources → different sets of processes see different resources
* Article's analogy → flats in one building complex: shared structure, separate addresses, names and utilities
* Namespaces → what a container can see | cgroups → what it can use

## The 7 namespaces

| Namespace | Isolates | In Docker |
|---|---|---|
| PID | Process list | nginx is PID 1 inside, some other PID on the host |
| NET | Interfaces, IPs, ports, routing | Own `eth0` (veth into `docker0`), 10 containers can all use port 80 |
| MNT | Filesystem view | Sees the OverlayFS image as `/`, not the host's files (compare `chroot`) |
| UTS | Hostname | `docker run --hostname web1` |
| IPC | Shared memory, message queues, semaphores | Containers can't touch each other's shared memory |
| USER | UID mapping | Root inside can map to an unprivileged user outside |
| CGROUP | View of `/sys/fs/cgroup` | Sees only its own cgroup tree |

* nginx log `1#1` → nginx is PID 1 inside its PID namespace

## Corrections to the article

* USER namespace → real point is security: container root ≠ host root
* Docker doesn't enable it by default → container root = real root unless `"userns-remap"` in `daemon.json` or rootless Docker (`docker-ce-rootless-extras`)
* There are 8 now → TIME namespace (kernel 5.6+) came after the article, Docker doesn't use it by default

## Lab: see namespaces

```bash
docker run -d --name ns-test nginx
PID=$(docker inspect -f '{{.State.Pid}}' ns-test)
echo $PID
sudo ls -l /proc/$PID/ns
sudo ls -l /proc/self/ns
sudo nsenter -t $PID -n ip a
sudo nsenter -t $PID -p -m ps aux
sudo lsns -p $PID
docker rm -f ns-test
```

* `docker inspect -f '{{.State.Pid}}'` → the container's PID on the host
* `/proc/$PID/ns` vs `/proc/self/ns` → different namespace IDs = separate namespaces from my shell
* `nsenter -n ip a` → inside the container's network namespace → only `lo` and `eth0`
* `nsenter -p -m ps aux` → container's own process list, nginx is PID 1
* `lsns -p` → every namespace the process belongs to

## Lab: a "container" without Docker

```bash
sudo unshare --pid --fork --mount-proc --uts bash
hostname fake-container
ps aux
exit
```

* bash is PID 1, hostname change doesn't touch the real host → core of what `runc` does, minus cgroups and the image filesystem

!!! question "Interview points"

    * What is a Linux namespace? → a kernel feature that gives a set of processes its own view of a resource (processes, network, mounts, hostname...)
    * Namespaces vs cgroups? → namespaces limit what a process can see; cgroups limit what it can use
    * Name the 7 namespaces → PID, NET, MNT, UTS, IPC, USER, CGROUP (plus TIME on newer kernels)
    * Is container root the same as host root? → by default yes; user namespace remapping or rootless Docker changes that
    * How do you get a shell in a container's network namespace from the host? → nsenter -t <pid> -n
    * Why can 10 containers all listen on port 80? → each has its own network namespace
