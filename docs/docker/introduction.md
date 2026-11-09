# Introduction

*Hands-on notes, Docker basics*

## The problem Docker solves

* "Works on my machine" → app works on laptop, breaks on server → different runtime version, missing library, different OS or config
* Docker's answer → ship the app together with everything it needs (code + runtime + libraries + config) as one sealed package
* Image → that sealed package | Container → a running copy of it
* Analogy → shipping containers: every ship, crane and truck handles the same standard box, doesn't care what's inside

## Container vs VM

| | Virtual machine | Container |
|---|---|---|
| Inside | Full OS with its own kernel | Only the app and its libraries |
| Kernel | Separate kernel per VM | Shares the host kernel |
| Startup | Tens of seconds to minutes | Milliseconds to seconds |
| Size | GBs | MBs |
| Isolation | Very strong (hardware level) | Good, but weaker (shared kernel) |
| Runs | Any OS | Linux containers need a Linux kernel |

* Analogy → VM = separate house (own foundation, plumbing) | container = flat in one building (shared foundation = kernel, own walls and door)
* Docker Desktop on Mac/Windows → secretly runs a small Linux VM and puts containers inside it
* Native Ubuntu → containers run directly on my kernel, no VM in between

## Kernel vs user space

* Kernel → core of the OS, talks to hardware, decides who gets CPU/RAM/disk/network → only one kernel runs on the machine
* User space → every program (bash, nginx, `dockerd`) → can't touch hardware, asks the kernel through system calls
* Every container on the machine shares the one host kernel → main difference from a VM
* Proof → nginx inside a container logs `OS: Linux 6.14.0-37-generic` = my host kernel

## What a container actually is

* Container = normal Linux process + namespaces + cgroups + layered filesystem
* Namespaces → what the process can **see** (own process list, network, files, hostname) → see [Namespaces](namespaces.md)
* cgroups → what the process can **use** (CPU, RAM, disk I/O, process count) → `--memory=512m` is enforced here
* Over the memory limit → kernel OOM killer kills it → exit code `137`
* OverlayFS → stacks read-only image layers + one writable layer into one `/` → see [Images & Storage](images-and-storage.md)
* Container lives only as long as its main process (PID 1) → main process exits = container stops

## Core objects

| Object | What it is | Analogy |
|---|---|---|
| Image | Read-only template: files + config + default command | Recipe / class |
| Container | Running (or stopped) instance of an image | Dish cooked from the recipe / object |
| Layer | One slice of an image's filesystem | One page of the recipe |
| Dockerfile | Text file with instructions to build an image | Recipe written down |
| Registry | Server that stores images | App store / library |
| Repository + tag | `nginx:1.27` → repo `nginx`, tag `1.27` | Book title + edition |
| Volume | Storage that outlives the container | External hard drive |
| Network | Virtual network containers join | Virtual switch |

* One image → many containers (same recipe, many dishes)

!!! question "Interview points"

    * Container vs VM? → VM has its own kernel and full OS; container is a process sharing the host kernel, so it is smaller and starts in milliseconds but isolation is weaker
    * What is a container, technically? → a normal Linux process with namespaces (what it sees), cgroups (what it uses) and a layered filesystem
    * Why does a container stop when its app exits? → the container lives only as long as its main process (PID 1)
    * Exit code 137? → process got SIGKILL, often the OOM killer after hitting the memory limit
    * Can a Linux container run on a Windows kernel natively? → no, containers share the host kernel; Docker Desktop runs a Linux VM for this
    * Image vs container? → image is the read-only template, container is a running instance of it with its own writable layer
