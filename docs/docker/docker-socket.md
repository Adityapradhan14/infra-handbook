# The Docker Socket

*Hands-on notes, Docker internals and Portainer*

## What it is

* Docker has two parts → the `docker` CLI is only a client, `dockerd` (the daemon) does the real work
* They talk over a REST API → the daemon listens on `/var/run/docker.sock` by default
* Unix socket → same-machine communication exposed as a file, permissions decide who can use it, no network involved
* `ls -l /var/run/docker.sock` → `srw-rw---- root docker`, so only `root` and the `docker` group
* `docker ps` → the CLI sends `GET /containers/json` through the socket and prints the reply
* Adding yourself to the `docker` group → avoids `sudo`, but see the warning below

```bash
curl --unix-socket /var/run/docker.sock http://localhost/containers/json
curl --unix-socket /var/run/docker.sock "http://localhost/containers/json?all=true"
```

* `[]` → the call worked, nothing is running
* `all=true` → include stopped containers

## Mounting the socket into a container

* A container is isolated → it has its own filesystem and cannot see `/var/run/docker.sock` on the host
* Mounting the socket is a [bind mount](volumes-and-bind-mounts.md) of one file, a volume cannot do this
* Inside the container the CLI now reaches the host's daemon

```bash
docker run -v /var/run/docker.sock:/var/run/docker.sock ...
docker run --mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock ...
```

* `docker images` inside the container → lists the host's images, proof it is the host daemon
* Used by → CI runners (Jenkins, GitLab runner), Portainer, Traefik, Watchtower
* Called Docker-out-of-Docker → containers started this way are siblings on the host, not children
* Docker-in-Docker → a separate daemon inside a privileged container, different thing
* `--network none` → does not help, the socket is a file mount, not a network path

## Why it is root on the host

* The daemon runs as root and does whatever the API asks
* Anyone who can reach the socket can start a container with the host's `/` mounted

```bash
# read-only demo, prints the host's hostname from inside a container
docker run --rm -v /:/host alpine cat /host/etc/hostname
```

* Replace `cat` with a write or `chroot /host sh` → root shell on the host
* `docker` group membership → same as root without `sudo`

!!! warning "Docker socket = root on the host"

    Only mount it into containers you would trust with root. A bug in a web app that has the socket mounted is a host takeover.

## Reducing the risk

* Don't mount it into untrusted or internet-facing containers
* `:ro` on the socket → only stops writes to the socket file, the API still accepts every command, so it is weak
* Socket proxy → `tecnativa/docker-socket-proxy` allows only chosen API calls, for example list containers
* Rootless Docker or Podman → the daemon is not root, so a breakout is not root
* Never expose the daemon on TCP `2375` (no TLS) → `2376` with TLS only, otherwise anyone on the network has root

## Lab: socket in a container

* Any image that ships the `docker` CLI works, for example `docker:cli`
* Same image, one flag difference

```bash
# 1. no socket
docker run --rm -d --name app1 --network none docker:cli sleep 600
docker exec -it app1 docker ps
#    Cannot connect to the Docker daemon at unix:///var/run/docker.sock
docker stop app1

# 2. socket mounted
docker run --rm -d --name app1 -v /var/run/docker.sock:/var/run/docker.sock --network none docker:cli sleep 600
docker exec -it app1 docker ps        # works, lists the host's containers
docker exec -it app1 docker images    # the host's images
docker inspect app1 | grep IPAddress  # empty, no network, still full control
docker stop app1
```

1. Without the mount → the CLI exists but there is no socket file to reach the daemon
2. With the mount → same file as the host, so the request reaches the host's `dockerd`
3. `IPAddress` is empty with `--network none` → the container still controls the host's Docker

## Lab: Portainer

* Portainer → web UI for Docker, runs as a container itself
* Socket bind mount → how it sees and controls Docker
* `portainer_data` volume → keeps the admin user and settings across container recreation
* Port `9443` is HTTPS only → `https://localhost:9443`, accept the self-signed certificate warning
* Setup token → printed in `docker logs portainer`, changes on every restart
* Setup window → about 5 minutes to create the admin user, then the page locks

```bash
docker run -d -p 8000:8000 -p 9443:9443 --name portainer \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:lts
```

### Errors I hit

| Symptom | Cause | Fix |
|---|---|---|
| `Client sent an HTTP request to an HTTPS server.` | Opened `http://localhost:9443` | Use `https://localhost:9443` |
| Dashboard shows 0 containers, 0 images while the environment says Up | Pinned Portainer `2.11.1` is too old for a Docker 29 daemon, logs show `client version 1.37 is too old. Minimum supported API version is 1.40` | Run `portainer/portainer-ce:lts` |
| `Your Portainer instance timed out for security purposes` | Admin user not created within about 5 minutes | `docker restart portainer`, then create the user quickly |
| `Request failed with status code 403` on Create user | Wrong or stale setup token | Read the new token from `docker logs portainer`, hard-reload the page, paste it exactly |

### Cleanup

* Removing the container keeps the volume → admin and settings survive
* `--restart=always` → it comes back after a reboot until the container is removed

```bash
docker rm -f portainer
docker volume rm portainer_data
docker rmi portainer/portainer-ce:lts
```

!!! tip "Quick revision"

    * Socket → the phone line to `dockerd`, a file at `/var/run/docker.sock`
    * Mounting it → bind mount, gives the container the host's Docker
    * Socket access → root on the host

!!! question "Interview points"

    * What is the Docker socket? → `/var/run/docker.sock`, the Unix socket the daemon listens on. The CLI and tools like Portainer use the REST API through it
    * Why is mounting it dangerous? → the daemon runs as root, so a process with the socket can start a container with the host's `/` mounted. It is root on the host
    * Does `--network none` protect a container that has the socket? → no, the socket is a file mount, not a network path
    * Why do CI runners mount it? → to start sibling containers on the host's daemon (Docker-out-of-Docker). Docker-in-Docker runs its own daemon in a privileged container instead
    * How do you make socket access safer? → rootless Docker or Podman, a socket proxy that allows only certain API calls, no mount into untrusted containers
    * Why is `docker` group membership a security concern? → it can reach the socket, which is equivalent to root
    * Why is exposing the daemon on TCP `2375` bad? → no TLS or auth, anyone on the network gets root. If you need remote access use `2376` with TLS
    * Why did Portainer show 0 containers on a newer Docker? → the daemon raised its minimum API version and an old Portainer client was rejected, so upgrade Portainer
    * Which two mounts does a Portainer container need and why? → the socket (bind mount, to control Docker) and a volume on `/data` (to keep its settings)
