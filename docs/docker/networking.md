# Networking

*Hands-on notes, how containers reach each other and the outside world*

## Basics first

* IP address → which building | `localhost` / `127.0.0.1` → my own machine
* Port → which door of that building (0–65535) → web server 80, SSH 22, Postgres 5432
* "Listening on port 80" → the program stands behind door 80, waiting for a knock
* IP + port → one specific service → `localhost:8000` = my machine, door 8000
* Private ranges → `10.x`, `172.16–31.x`, `192.168.x` → not reachable from the internet directly → Docker uses `172.17.x.x`
* Network interface → real or virtual network card → `wlo1` Wi-Fi | `lo` loopback | `docker0` Docker's switch | `CloudflareWARP` VPN
* NAT → rewrites addresses on packets → how a home router shares one public IP
* iptables/nftables → kernel firewall and packet-rewriting rules → Docker writes rules here automatically
* DNS → names to IPs

## `docker0`

* `docker0` → virtual network switch made of software → a Linux bridge
* Created by `dockerd` at startup → stays with zero containers (`DOWN`, `NO-CARRIER` = nothing plugged in)
* Has IP `172.17.0.1` → the gateway for containers
* Containers get IPs from the same range → `172.17.0.2`, `172.17.0.3` ...
* Container doesn't know the way to google.com → sends to its gateway `docker0` → host sends it out via Wi-Fi
* Only for the default network → `docker network create mynet` → another bridge (`br-...`), another range (e.g. `172.18.0.x`)

## veth pairs

* veth pair → virtual cable with two ends
* One end inside the container's network namespace → renamed `eth0`
* Other end on the host (`veth3a9f1b2`) → plugged into `docker0`
* Each container = own network namespace = own IP, own ports, own routing → two containers can both use port 80

```
   Internet
       │
    wlo1 (192.168.1.x)         ← my real Wi-Fi
       │   NAT (iptables)
    docker0 (172.17.0.1)       ← virtual switch
     │          │
  vethA       vethB            ← host ends of virtual cables
     │          │
  [eth0]      [eth0]
 container1  container2
 172.17.0.2  172.17.0.3
```

## Three packet journeys

* Container A → container B → A's `eth0` → veth → `docker0` → veth → B's `eth0` → never leaves the laptop
* Container → internet → `docker0` → iptables MASQUERADE swaps `172.17.0.2` for the host IP → out through `wlo1` → reply translated back
* Outside → container (`-p 8080:80`) → arrives at host:8080 → iptables DNAT rewrites to `172.17.0.2:80` → `docker0` → nginx

## Port forwarding (`-p`)

* Container's doors are not the host's doors → host door 80 and container door 80 are different doors
* No `-p` → `localhost:8000` = connection refused → nobody behind the host's door
* `-p 8000:80` → pipe from host door 8000 to container door 80 → HOST:CONTAINER, outside:inside
* Left → what I type in the browser | right → where the app is actually waiting
* nginx never sees port 8000, only 80
* `-p 8000:80` → all interfaces, other Wi-Fi devices can reach it
* `-p 127.0.0.1:8000:80` → only my own machine
* Two containers can both use container port 80 → each has its own namespace
* Two containers can't both use host port 8000 → host has only one door 8000
* `EXPOSE 80` / `PORTS 80/tcp` in `docker ps` → documentation only, nothing published
* Published → `PORTS 0.0.0.0:8080->80/tcp`
* Published ports bypass UFW → Docker's iptables rules run before UFW's
* `PORTS` example → `8888/tcp, 0.0.0.0:8001->80/tcp, [::]:8001->80/tcp`
* `8888/tcp` → EXPOSE only | `0.0.0.0:8001->80/tcp` → `-p` on every IPv4 address | `[::]:8001->80/tcp` → same for IPv6

## Network drivers

* Driver → the type of network → how Docker wires the container

| Driver | How it wires the container | Container gets | When |
|---|---|---|---|
| `bridge` | veth cable into a software switch on this host (default) | Own IP from the bridge's range | Most single-host use |
| `host` | Nothing, uses the host's network namespace | Host's IPs and ports | Max performance, host-level tools, port conflicts possible |
| `null` (`none`) | Nothing | Only `lo` | Fully isolated jobs |
| `overlay` | Bridge spanning multiple hosts, tunnels between machines | IP valid across hosts | Swarm / multi-host |
| `macvlan` / `ipvlan` | Straight onto the physical LAN | IP from the router, like a real device | Container must look like a real device |

* `docker network ls` → mine shows `bridge` (= `docker0`), `host`, `none`, `kind` (bridge made by kind, Kubernetes-in-Docker)
* `host` and `none` → built-in modes, always exist, can't be deleted
* `docker network` → `connect`, `create`, `disconnect`, `inspect`, `ls`, `prune`, `rm`

## User-defined bridge networks

* `docker network create custom --driver bridge` → new, separate switch → host interface `br-<network id>` (e.g. `br-d0340428...`)
* Subnet → Docker picks the next free range → `172.17` = `docker0`, `172.18` = `kind`, so `custom` got `172.19.0.0/16`
* Gateway → `172.19.0.1` → the bridge's own IP, same role as `docker0`'s `172.17.0.1`
* IPs handed out in order → first container `.2`, then `.3`...
* `--network custom` on `docker run` → join that network instead of the default
* `docker network inspect custom` → subnet, gateway, attached containers with IP and MAC
* `IPsInUse: 6` → 3 containers + 3 reserved (`.0` network address, `.1` gateway, `.255.255` broadcast)
* `DynamicIPsAvailable: 65530` → `/16` = 65,536 addresses − 6
* `docker network rm custom` → only works when no container is attached

## DNS by name

* Default `docker0` → no DNS → containers reach each other only by IP
* User-defined network → built-in DNS server at `127.0.0.11` inside each container → every container's name registered → reach each other by name (`postgres:5432`)
* `ping app4` → resolves to `app4.custom` → `<name>.<network>`
* Container IPs change on every restart, names don't → always use a user-defined network for apps that talk to each other
* Compose creates such a network automatically → services find each other by service name

## Isolation and multiple networks

* Networks are isolated from each other → container on `custom` can't reach one on `docker0`, by IP or name → Docker's iptables rules block traffic between bridges
* `docker network connect custom app1` → plugs a second cable into a running container
* app1 then has two network cards → `eth0` `172.17.0.2` on `docker0` + `eth1` `172.19.0.4` on `custom` → check with `docker exec app1 ip -br a`
* Only way across two networks → a container connected to both
* `docker network disconnect custom app1` → unplug it again

## Host network mode

* `docker run --rm -d --name nodeexporter --network host prom/node-exporter`
* No own network namespace → no `docker0`, no veth, no `-p` → listens on the host's port 9100 directly → `PORTS` empty
* Why for Node Exporter → it reports the host's metrics, including real interfaces (`wlo1`, `docker0`) → in bridge mode it would see only its own `eth0`
* Trade-off → no network isolation, port 9100 taken on the host itself → two can't run at once
* Fuller recommended run → `--network host --pid host -v /:/host:ro,rslave prom/node-exporter --path.rootfs=/host` → also reads host processes and disks

| `docker inspect` field | Value | Meaning |
|---|---|---|
| `NetworkMode` | `host` | No own network namespace |
| `IPAddress` | `""` | No container IP, uses the host's |
| `SandboxKey` | `/var/run/docker/netns/default` | The host's network namespace |
| `Ports` / `PortBindings` | `{}` | Nothing to forward |
| `ExposedPorts` | `9100/tcp` | EXPOSE, documentation only |
| `Hostname` | host's hostname | Shared with the host too |
| `AutoRemove` | `true` | `--rm` |
| `User` | `nobody` | Runs unprivileged |
| `Entrypoint` | `/bin/node_exporter` | No CMD, ENTRYPOINT is the whole command |
| `GraphDriver` | `LowerDir`, `UpperDir`, `MergedDir` | Read-only image layers, writable layer, the merged `/` → see [Images & Storage](images-and-storage.md) |

## My machine

* `virbr0` (`192.168.122.x`) → libvirt/KVM bridge, separate, no conflict with Docker
* Cloudflare WARP → takes over routes, MTU 1300 → first suspect if containers can't reach the internet or pulls are slow

## Lab: ports and `docker0`

```bash
docker run --rm -d --name test1 nginx
curl http://localhost:8000
docker inspect -f '{{.NetworkSettings.IPAddress}}' test1
curl http://172.17.0.2
docker stop test1

docker run --rm -d --name test2 -p 8000:80 nginx
curl http://localhost:8000
docker stop test2

docker run --rm -d --name web1 -p 8001:80 nginx
docker run --rm -d --name web2 -p 8002:80 nginx
sudo iptables -t nat -L DOCKER -n
docker stop web1 web2

ip -br addr show docker0
bridge link
```

* No `-p` → `localhost:8000` refused, but the container IP answers → nginx was there, just behind the container's door
* With `-p 8000:80` → `localhost:8000` returns HTML
* `iptables -t nat -L DOCKER` → `dpt:8001 to:172.17.0.x:80` → the DNAT rule Docker wrote
* `bridge link` → one `veth...` per running container plugged into `docker0` → gone after stop

| Symptom | Cause | Fix |
|---|---|---|
| `PORTS` shows only `80/tcp`, browser can't reach nginx | No `-p`, `80/tcp` is just EXPOSE | `docker run -d -p 8080:80 nginx` |
| `localhost:8000` connection refused | Nothing published on host port 8000 | Add `-p 8000:80` |

## Lab: default bridge vs custom network

```bash
docker network ls
docker run --rm -d --name app1 -p 8000:80 kiran2361993/troubleshootingtools:v1
docker run --rm -d --name app2 -p 8001:80 kiran2361993/troubleshootingtools:v1
docker inspect app1 | grep -i IPAddress
docker inspect app2 | grep -i IPAddress
docker exec -it app1 bash
ping 172.17.0.3
exit

docker network create custom --driver bridge
docker run --rm -d --name app3 -p 8003:80 --network custom kiran2361993/troubleshootingtools:v1
docker run --rm -d --name app4 -p 8004:80 --network custom kiran2361993/troubleshootingtools:v1
docker inspect app3 | grep -i IPAddress
docker exec -it app3 bash
ping 172.19.0.3
exit

docker network connect custom app1
docker network inspect custom
docker exec -it app1 bash
ping app4
ping app3
ping app2
exit
docker stop $(docker ps -aq)
```

* app1 `172.17.0.2` → app2 `172.17.0.3` by IP → works, ~0.1 ms → app1 `eth0` → veth → `docker0` → veth → app2
* `ttl=64` unchanged → no router in between, same switch
* app3 `172.19.0.2` → app4 `172.19.0.3` → works on `custom`
* After `network connect` → app1 gets `172.19.0.4` on `custom` as well

| From app1 | Result | Why |
|---|---|---|
| `ping 172.19.0.3` | Works | app1 now has a cable on `custom` |
| `ping app4` | Works, `app4.custom` | Built-in DNS on the user-defined network |
| `ping app3` | Works | Same |
| `ping app2` | `Name or service not known` | app2 only on the default bridge → no DNS there (`ping 172.17.0.3` still works) |

## Lab: Node Exporter on the host network

```bash
docker run --rm -d --name nodeexporter --network host prom/node-exporter
docker ps
docker inspect nodeexporter
curl -s localhost:9100/metrics | head
curl -s localhost:9100/metrics | grep node_network_receive_bytes_total
docker stop nodeexporter
docker network rm custom
docker network ls
```

* `docker ps` → `PORTS` empty → no forwarding in host mode
* `node_network_receive_bytes_total` → lists my real interfaces (`wlo1`, `docker0`, `CloudflareWARP`) → it sees the host's network

| Symptom | Cause | Fix |
|---|---|---|
| `ping app2: Name or service not known` | app2 is on the default bridge, which has no DNS | Put both on a user-defined network, or use the IP |
| `unknown flag: --netwrok` | Typo | `--network host` |
| `docker network rm` fails | Containers still attached | Stop or disconnect them first |

!!! question "Interview points"

    * What is docker0? → a Linux bridge (software switch) created by dockerd; containers plug into it via veth pairs and use 172.17.0.1 as their gateway
    * What is a veth pair? → a virtual cable; one end is eth0 inside the container, the other is plugged into the bridge on the host
    * What does -p 8080:80 mean? → host port 8080 forwards to container port 80 (HOST:CONTAINER) via an iptables DNAT rule
    * Why can't I reach a container without -p? → its IP is private to the host; nothing listens on the host port
    * Does EXPOSE publish a port? → no, it only documents it
    * How does a container reach the internet? → through docker0, then iptables MASQUERADE rewrites its source IP to the host's
    * Why can two containers use port 80 but not the same host port? → each has its own network namespace, but the host has only one of each port
    * Default bridge vs user-defined network? → user-defined networks have built-in DNS so containers reach each other by name
    * Why does a published port ignore UFW? → Docker's iptables rules are evaluated before UFW's
    * What is a network driver? → the type of network, i.e. how Docker wires the container: bridge, host, none, overlay, macvlan/ipvlan
    * Can a container on one user-defined network reach a container on another? → no, bridges are isolated by iptables; connect the container to both networks to cross
    * How do you add a running container to another network? → docker network connect <network> <container>; it gets a second interface (eth1)
    * Which DNS server do containers on a user-defined network use? → Docker's embedded DNS at 127.0.0.11
    * Why use names instead of container IPs? → IPs change when containers restart, names stay the same
    * When would you use --network host? → when the container must see or serve on the host's network directly, e.g. Node Exporter; you lose isolation and can get port conflicts
    * Why does docker ps show no ports in host mode? → nothing is forwarded; the app listens on the host's port directly
    * Why does a /16 network show 65530 available IPs with 3 containers? → 65,536 minus the network address, gateway, broadcast and the 3 containers
