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

## User-defined networks and DNS

* Default `docker0` → containers reach each other only by IP
* Own network (`docker network create mynet`) → built-in DNS at `127.0.0.11` → reach each other by name (`postgres:5432`)
* Compose creates such a network automatically → services find each other by service name

| Driver | Meaning | When |
|---|---|---|
| `bridge` | Private virtual network on this host (default) | Most single-host use |
| `host` | No isolation, uses host network directly | Max performance, port conflicts possible |
| `none` | No network | Fully isolated jobs |
| `overlay` | Network across multiple hosts | Swarm / multi-host |
| `macvlan` | Own MAC and IP on the physical LAN | Container looks like a real device |

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
