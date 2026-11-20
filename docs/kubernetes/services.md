# Services

## The problem Services solve

* Pods are **temporary** → crash, rescheduled, replaced in a rollout → every new Pod gets a **new IP**
* Frontend talks to backend by Pod IP → breaks the next time a backend Pod is replaced
* 3 backend replicas → which one should the frontend call? → it would need its own load-balancing logic
* Some Pods must be reachable **inside** the cluster only (backend), some from **outside** (frontend)

```
Without a Service:  User ─▶ Frontend Pod (IP keeps changing) ─▶ Backend Pod (IP keeps changing)   ✗

With Services:      User ─▶ frontend-svc ─▶ Frontend Pod ─▶ backend-svc ─▶ Backend Pod           ✓
```

## What a Service is

* A **stable front door** in front of a group of Pods
* Gives →
    * a **fixed virtual IP** (ClusterIP) that never changes while the Service exists
    * a **DNS name** → `backend-svc` (short) or `backend-svc.default.svc.cluster.local` (full)
    * **load balancing** across all matching **Ready** Pods
    * **automatic tracking** → Pods come and go, the Service's list updates by itself
* Analogy → customer-care number → which employee picks up keeps changing, the number stays the same
    * number = Service | employees = Pods | caller = frontend

## Pod networking vs Services

* Common confusion → "Services let Pods on different nodes talk" → **not quite**
* Pods can **already** reach each other by Pod IP, same node or different node → that is the **CNI plugin's** job (Calico, Flannel, Cilium, kindnet in kind) → every Pod gets a unique IP, all nodes joined into one flat network
* The **Service** adds what raw Pod IPs can't give → a stable name/IP + load balancing + auto-updating list of Pods

| | CNI (Pod network) | Service |
|---|---|---|
| Analogy | The roads | The address board / reception |
| Gives | Every Pod a unique IP, cross-node delivery | Stable IP + DNS name, load balancing |
| Without it | Pods can't reach each other at all | Pods can reach each other, but must track changing IPs themselves |

* A Service works the same whether its Pods are on one node or spread across many

## How a Service finds its Pods (labels and selectors)

* A Service never lists Pod names or IPs → it has a **selector** → "send traffic to every Pod with these labels"
* Kubernetes keeps checking → which Pods have this label **right now**? → those become the Service's **endpoints**

### The label that connects everything

```yaml
# Deployment
spec:
  selector:
    matchLabels:
      app: backend       # (2) Deployment finds ITS Pods by this label
  template:
    metadata:
      labels:
        app: backend     # (1) every Pod gets this label (sticker)
---
# Service
spec:
  selector:
    app: backend         # (3) Service finds Pods to send traffic to by this label
```

| Where | What it does |
|---|---|
| `template.metadata.labels` | **Puts** the label on each new Pod |
| Deployment `selector.matchLabels` | Deployment **counts** its own Pods by the label |
| Service `selector` | Service **finds** Pods to route to by the label |

* Deployment and Service **don't know about each other** → they're linked only through the Pods' labels
* Change the label in one place and not the others → things break silently

### Rules

* **Automatic and live** →
    * Pod dies → removed from the Service
    * New Pod comes up → added
    * Scale 3 → 5 → all 5 added, Service YAML untouched
* **Only Ready Pods** → a Pod still starting or failing its readiness probe is **not** added → no traffic until Ready
* **Same namespace only** → a Pod with `app: backend` in another namespace is ignored
* **Any Pod with the label gets traffic** → even a random test Pod I accidentally label `app: backend` → keep labels specific
* **Doesn't care who created the Pod** → delete the Deployment, create matching Pods another way → Service still routes to them

### Where the list lives → EndpointSlices

* The **EndpointSlice controller** (inside kube-controller-manager) writes the current Ready `PodIP:targetPort` list into **EndpointSlice** objects
* Old API = `Endpoints` object → still shown in `kubectl describe svc` as the `Endpoints:` line

```bash
kubectl describe svc backend-svc                                        # Endpoints: line
kubectl get endpointslices -l kubernetes.io/service-name=backend-svc
```

* Watch it update live →

```bash
kubectl get endpointslices -l kubernetes.io/service-name=backend-svc -w   # terminal 1
kubectl scale deployment backend-deploy --replicas=5                      # terminal 2 → 2 new IPs appear
```

* **`Endpoints` empty** = selector matches no Pods OR matching Pods aren't Ready → the most common Service bug

## Ports, from zero

### What a port is

* A machine has **one IP** but runs many apps → a message arrives → which app is it for? → the **port** decides
* Each app listens on its own number → web server 80, MySQL 3306, SSH 22
* Full address = **IP : port** → which machine : which app on it
* Analogy → IP = apartment building | port = flat number | courier needs both

### The two ports of a Service

```
frontend  ─▶  backend-svc : 9090   ─▶   pod : 5678
              (Service IP) port         (Pod IP) targetPort
```

* **`port`** → the port the **Service** listens on → what **callers** use → `backend-svc:9090` → **I choose** it, any number
* **`targetPort`** → the port the **app inside the Pod** listens on → where traffic finally lands → **the app decides** it, I just have to tell the Service what it is
* The node swaps **both** parts → Service IP → Pod IP **and** 9090 → 5678

| Hotel | Kubernetes |
|---|---|
| Reception | Service |
| Counter 9090 (guests go here) | `port` |
| Room 5678 (the person is actually here) | `targetPort` |
| Person in the room | The app (http-echo) |
| Guest | The caller (frontend) |

* Memory trick → **target = the app** → shooting an arrow: fire from `port`, it lands on the `targetPort`
* Who uses what →
    * **Service** → one IP (`10.96.74.12`), accepts traffic on **9090**
    * **Caller** → sends to `backend-svc:9090` → any other port → nothing answers
    * **Pods** → each has its **own different IP** (`10.244.2.14`, `10.244.1.14`, `10.244.2.15`) but **all listen on the same 5678** (same app)

```
caller ─▶ 10.96.74.12:9090 ─┬─▶ 10.244.2.14:5678
          (Service)         ├─▶ 10.244.1.14:5678
                            └─▶ 10.244.2.15:5678
                               (different IPs, same port)
```

### Why two numbers at all

* Caller doesn't need to know the app's real port
* App moves from 5678 → 8000 → change only `targetPort` → callers still use `:9090` → nothing else breaks
* In practice they are often the same → `port: 80, targetPort: 80` → keeps it simple

### Examples

| YAML | Caller uses | App listens on |
|---|---|---|
| `port: 9090, targetPort: 5678` | `backend-svc:9090` | 5678 |
| `port: 80, targetPort: 3000` | `backend-svc:80` | 3000 |
| `port: 80, targetPort: 8080` | `backend-svc:80` | 8080 |

### Wrong targetPort = classic bug

* `targetPort` doesn't match the app's real port (app on 80, I wrote 5678) →
    * Service is created fine ✓ | Pods are `1/1 Running` ✓ | `Endpoints` shows IPs ✓
    * but every request fails → **connection refused** / browser says **empty response** → the node forwards to a port where **nothing is listening**
* Fix → set `targetPort` to the port the app really uses

### How to find which port an app uses

* **nginx listens on 80 by default** → set in its config (`listen 80;` in `/etc/nginx/conf.d/default.conf`)
* `hashicorp/http-echo` listens on **5678** by default
* Ways to check any image →
    1. The image's page on Docker Hub → docs mention the port
    2. `EXPOSE` in the image → only a **label** from the image author, usually right, not guaranteed
    3. Look inside the running container → what is **actually** listening (most reliable)

```bash
docker inspect nginx --format '{{.Config.ExposedPorts}}'                          # map[80/tcp:{}]
kubectl exec -it deploy/frontend-deploy -- cat /etc/nginx/conf.d/default.conf | grep listen
```

* `containerPort` in a Deployment (`ports: - containerPort: 80`) → **documentation only** → does not open or block anything → Service's `targetPort` must still match the real port

| App | Default port |
|---|---|
| nginx / Apache (HTTP) | 80 |
| HTTPS | 443 |
| hashicorp/http-echo | 5678 |
| Node.js apps | often 3000 |
| Flask | 5000 |
| Spring Boot / Tomcat | 8080 |
| MySQL | 3306 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| MongoDB | 27017 |
| DNS | 53 |

* Defaults only → any app can be reconfigured → when something breaks, check the real config

## Service manifest anatomy

```yaml
apiVersion: v1
kind: Service
metadata:
  name: backend-svc          # also becomes its DNS name
spec:
  type: ClusterIP            # what kind of Service
  ports:                     # which door
    - protocol: TCP          # default TCP, can be skipped
      port: 9090             # Service's port (callers use this)
      targetPort: 5678       # app's port inside the Pod
  selector:                  # which Pods
    app: backend
```

* Three parts under `spec` → **type, ports, selector**
    * **type** → what kind? → ClusterIP / NodePort / LoadBalancer / ExternalName
    * **ports** → which door? → `port` (counter) + `targetPort` (room) (+ `nodePort` for NodePort)
    * **selector** → which Pods? → label to match
* Memory trick → **T-P-S** → "Tea, Pakoda, Samosa" → what kind, which door, which pods
* `type` is optional → skipped = `ClusterIP` | `ports` and `selector` are almost always written
* `port` can have a `name` → shown as `<unset>` in `describe` when not set → optional, nothing wrong
* Imperative shortcut →

```bash
kubectl expose deployment backend-deploy --name=backend-svc --port=9090 --target-port=5678
kubectl expose deployment backend-deploy --port=9090 --target-port=5678 --dry-run=client -o yaml   # generate YAML
```

## Service types

| Type | Reachable from | What it adds |
|---|---|---|
| **ClusterIP** (default) | Inside the cluster only | Stable virtual IP + DNS name + load balancing |
| **NodePort** | Outside, at `<anyNodeIP>:<nodePort>` | ClusterIP + same port (30000–32767) opened on every node |
| **LoadBalancer** | Outside, at one external IP/hostname | NodePort + a cloud load balancer in front |
| **ExternalName** | Inside the cluster | Just a DNS alias (CNAME) to an outside name, no IP, no Pods |
| Headless (`clusterIP: None`) | Inside the cluster | No virtual IP, DNS returns each Pod's IP directly |

* They **stack** →

```
LoadBalancer  =  NodePort + cloud load balancer
NodePort      =  ClusterIP + port on every node
ClusterIP     =  internal fixed address
```

### Office-building analogy

| Building | Kubernetes |
|---|---|
| Office building complex | Cluster |
| Individual buildings | Nodes |
| Departments (HR, Finance) | Pods |
| Internal phone extensions | **ClusterIP** → only works inside the complex |
| Front-desk phone number of each building | **NodePort** → outsiders call a building's front desk |
| Call centre with one number | **LoadBalancer** → routes to any working front desk |
| IT support speed-dial 111 | **ExternalName** → shortcut to an outside party |

## ClusterIP

* Default type → reachable **only inside** the cluster → for Pod-to-Pod traffic (frontend → backend, backend → cache)
* Gets a virtual IP from the **Service CIDR** (`10.96.0.0/12` in kind) → not on any machine, Pod or network card

### The simple story

1. Frontend wants `backend-svc` → computers need an IP, not a name → asks the cluster's **phonebook** (CoreDNS) → answer `10.96.74.12`
2. Frontend sends the request to `10.96.74.12`
3. `10.96.74.12` is **fake** → nobody owns it → it exists only as a rule on every node
4. As the packet leaves, the node checks its rule → "anything to `10.96.74.12`? send it to one of the 3 backend Pods" → picks one, changes the address on the packet
5. That Pod replies → on the way back the node changes the reply's address back to `10.96.74.12` → frontend thinks the fake address answered

* Analogy → letter to "PO Box 9090" → post office rule: letters to that box go to any free employee → reply comes back stamped "PO Box 9090"
* Two things to remember →
    * the **Service IP is fake** → just a rule on every node
    * the **node swaps** the fake address for a real Pod's address, and swaps it back on the reply

### What happens when the Service is created

1. **kubectl → API server** → YAML validated, stored in **etcd** → at this point only a database record, nothing running
2. **IP allocated** → API server picks a free IP from the Service CIDR → `10.96.74.12` → virtual, not attached anywhere
3. **Pods found** → EndpointSlice controller reads `selector: app=backend` → finds all **Ready** Pods with that label → adds `targetPort` →
   `10.244.2.14:5678, 10.244.1.14:5678, 10.244.2.15:5678` → the `Endpoints:` line
4. **DNS record** → **CoreDNS** (Pods in `kube-system`) watches the API server → adds
   `backend-svc.default.svc.cluster.local → 10.96.74.12`
5. **Rules on every node** → **kube-proxy** (one per node, a DaemonSet) watches Services and EndpointSlices → writes **iptables** NAT rules on its node:
   "packet to `10.96.74.12:9090` → change destination to one of the 3 endpoints, pick randomly"

* Setup done → no process "runs" the Service → it's a DNS record + iptables rules on every node

### What happens on `curl backend-svc:9090` (packet by packet)

1. **App needs an IP** → can't connect to a name
2. **Pod knows where DNS is** → kubelet wrote `/etc/resolv.conf` into the Pod:
    ```
    search default.svc.cluster.local svc.cluster.local cluster.local
    nameserver 10.96.0.10
    options ndots:5
    ```
    * `nameserver 10.96.0.10` → send DNS questions here → that is the **kube-dns** Service (in front of the CoreDNS Pods)
    * `search ...` → short name `backend-svc` → try `backend-svc.default.svc.cluster.local` first
    * `ndots:5` → names with fewer than 5 dots get the search suffixes tried first
3. **DNS question and answer** → "what is `backend-svc.default.svc.cluster.local`?" → CoreDNS → `10.96.74.12`
4. **App sends the packet** → from `10.244.1.5:<random port>` (frontend Pod) → to `10.96.74.12:9090`
5. **Packet leaves the Pod** → through the Pod's **veth pair** (virtual cable: one end in the Pod, one end on the node) → arrives in the **node's kernel**
6. **iptables catches it** → rule matches `10.96.74.12:9090` → picks an endpoint at random, e.g. `10.244.2.15:5678` → **DNAT** (destination NAT):
    * before → to `10.96.74.12:9090`
    * after → to `10.244.2.15:5678`
    * kernel records the rewrite in **conntrack** (connection tracking table) so it can undo it for the reply
7. **Routing** → is `10.244.2.15` on this node?
    * yes → delivered straight through that Pod's veth
    * no → the **CNI** carries it to the right node, which delivers it
8. **Backend Pod receives it** on `:5678` → http-echo accepts → doesn't know a Service was involved → sees the request coming from `10.244.1.5`
9. **Reply** → from `10.244.2.15:5678` to `10.244.1.5` → passes back through the frontend's node
10. **conntrack undoes the rewrite** → source changed back:
    * before → from `10.244.2.15:5678`
    * after → from `10.96.74.12:9090`
    * why → the app talked to `10.96.74.12:9090`; a reply from any other address would be rejected ("I never talked to you")
11. **Frontend gets the answer** → from `10.96.74.12:9090` → never knows which Pod replied

* The "Service" is really just a **destination rewrite on the node** → no load-balancer machine, no proxy process in the data path

### When a backend Pod dies

* Pod `10.244.2.15` crashes → EndpointSlice controller removes it → 2 endpoints
* kube-proxy on every node updates its rules → only the 2 remaining Pods
* Deployment's ReplicaSet creates a replacement → **new IP**, e.g. `10.244.1.20` → once Ready → added to endpoints → rules updated again
* Frontend keeps calling `backend-svc:9090` → notices nothing → that's the whole point of a Service

### Two IP ranges

| Range (kind defaults) | What | Stable? |
|---|---|---|
| `10.96.x.x` | Service IPs (ClusterIPs) | Yes, for the Service's lifetime |
| `10.244.x.x` | Pod IPs | No, change on every restart |

* Each node usually gets its own Pod range → `10.244.1.x` on one node, `10.244.2.x` on another → endpoints from both ranges = Pods spread over 2 nodes, Service treats them as one group

### Seeing the iptables rules

* kind nodes are Docker containers → look inside one

```bash
docker exec -it <node-name> iptables -t nat -L KUBE-SERVICES -n | grep backend-svc   # gives KUBE-SVC-XXXX
docker exec -it <node-name> iptables -t nat -L KUBE-SVC-XXXX -n
```

* 3 rules with probabilities ≈ `0.333`, `0.5`, then the rest →
    * rule 1 catches 1/3 of traffic
    * rule 2 catches half of the remaining 2/3 → 1/3
    * rule 3 takes what's left → 1/3
    * → each Pod gets an equal share, chosen randomly per new connection

### Reading `kubectl describe svc`

```
Name:                     backend-svc
Namespace:                default
Selector:                 app=backend
Type:                     ClusterIP
IP:                       10.96.74.12
Port:                     <unset>  9090/TCP
TargetPort:               5678/TCP
Endpoints:                10.244.2.14:5678,10.244.1.14:5678,10.244.2.15:5678
Session Affinity:         None
Internal Traffic Policy:  Cluster
```

| Field | Meaning |
|---|---|
| `Selector` | Label used to find Pods |
| `Type` | ClusterIP → internal only |
| `IP` | Fixed virtual IP → survives Pods being replaced |
| `Port: <unset> 9090/TCP` | `<unset>` = this port has no name (optional) → Service listens on 9090 |
| `TargetPort` | App's port inside the Pod |
| `Endpoints` | Real `PodIP:targetPort` of every Ready matching Pod → **first thing to check when debugging** |
| `Session Affinity: None` | Each new connection can go to any Pod → `ClientIP` = same client keeps hitting the same Pod |
| `Internal Traffic Policy: Cluster` | In-cluster traffic may go to Pods on any node (`Local` = only Pods on the caller's node) |

### DNS names of a Service

| Called from | Name that works |
|---|---|
| Same namespace | `backend-svc` |
| Other namespace | `backend-svc.<namespace>` |
| Anywhere (full name, FQDN) | `backend-svc.<namespace>.svc.cluster.local` |

## Lab: frontend + backend with ClusterIP

```yaml
# backend.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-deploy
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
        - name: backend-container
          image: hashicorp/http-echo          # tiny test server, listens on 5678
          args:
            - "-text=Hello from backend :)"   # text it replies with
---
apiVersion: v1
kind: Service
metadata:
  name: backend-svc
spec:
  type: ClusterIP
  ports:
    - protocol: TCP
      port: 9090
      targetPort: 5678
  selector:
    app: backend
```

* `---` → separates two objects in one file
* `http-echo` → replies to every request with the `-text` value → **5678** is its default port → that's where `targetPort: 5678` comes from

```yaml
# frontend.yaml (Deployment part)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend-deploy
spec:
  replicas: 3
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
        - name: frontend-container
          image: nginx
          ports:
            - containerPort: 80   # documentation only
```

```bash
kubectl apply -f backend.yaml -f frontend.yaml
kubectl get pods -o wide                     # match Pod IPs with the Endpoints line
kubectl get svc backend-svc
kubectl describe svc backend-svc             # Endpoints → 3 IPs with :5678

# call the backend from inside the cluster
kubectl exec -it deploy/frontend-deploy -- curl backend-svc:9090      # Hello from backend :)
kubectl run test --rm -it --image=busybox -- wget -qO- backend-svc:9090

# see each step
kubectl run test --rm -it --image=busybox -- cat /etc/resolv.conf     # DNS settings in a Pod
kubectl run test --rm -it --image=busybox -- nslookup backend-svc     # name → ClusterIP
```

* Break it on purpose → change `targetPort` to `5000` → apply → curl fails (nothing on 5000) → change back → works

## NodePort

### The problem

* ClusterIP works only **inside** the cluster → my laptop, browser or a user on the internet can't reach `10.96.x.x`
* Need a way in from **outside**

### What NodePort does

* "Open the **same port number** on **every node**. Anything arriving there goes to my Service."
* Port range → **30000–32767** (configurable on the API server, best left alone) → avoids clashing with normal system ports
* From outside → `http://<any node IP>:<nodePort>`
* Analogy → side door numbered 31000 on **every floor** of the building → walk into any floor's door 31000 → all lead to the same reception → works even on a floor with no backend Pods
* A NodePort Service **is still a ClusterIP Service** → gets a ClusterIP, in-cluster callers still use `svc:port` → NodePort only **adds** the outside door

### Now three ports

```
outside user ─▶ nodeIP:31000 ─▶ Service:80 ─▶ pod:80
                 nodePort        port          targetPort
```

| Field | What | Who uses it |
|---|---|---|
| `nodePort` | Port opened on every node (30000–32767) | **Outside** users |
| `port` | Service's own port on its ClusterIP | Pods **inside** the cluster |
| `targetPort` | App's port in the Pod | Where traffic finally lands |

```yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend-svc
spec:
  type: NodePort
  ports:
    - protocol: TCP
      port: 80          # ClusterIP port, in-cluster callers
      targetPort: 80    # nginx listens on 80
      nodePort: 31000   # opened on every node (30000-32767)
  selector:
    app: frontend
```

* `nodePort` omitted → Kubernetes picks a random free one in 30000–32767
* Set it explicitly when something outside depends on the number (kind `extraPortMappings`, firewall rules)
* One `nodePort` belongs to **one Service** cluster-wide → two Services can't both use 31000
* `kubectl get svc` shows `80:31000/TCP` → read as `port:nodePort`

### `kubectl describe` of a NodePort Service

```
Type:                     NodePort
IP:                       10.96.199.133
Port:                     <unset>  80/TCP
TargetPort:               80/TCP
NodePort:                 <unset>  31000/TCP
Endpoints:                10.244.2.10:80,10.244.1.9:80,10.244.1.10:80
External Traffic Policy:  Cluster
```

* Still has an `IP` → proof NodePort is built on ClusterIP

### What happens on a request from outside

1. User → `172.18.0.4:31000` (Node 2's IP) → arrives at Node 2's network interface
2. kube-proxy wrote a rule on **every** node → "anything to port 31000 on a node IP → frontend-svc"
3. iptables picks an endpoint, e.g. `10.244.1.10:80` → **DNAT**
4. `10.244.1.10` may be on a **different node** → CNI carries it there → that's why any node's door works
5. **SNAT** (extra step NodePort adds) → Node 2 also rewrites the **source** to its own IP → otherwise the other node would reply straight to the user and the user would reject it
    * side effect → nginx sees **Node 2's IP**, not the user's real IP
6. Reply → conntrack reverses both rewrites → user gets the answer from `172.18.0.4:31000`

```
NodePort (31000) → ClusterIP (80) → Pod (80)
```

### External Traffic Policy

| | `Cluster` (default) | `Local` |
|---|---|---|
| Node sends traffic to | Pods on **any** node | Only Pods on **itself** |
| Works through every node | Yes | Only nodes running a matching Pod (others drop it) |
| Extra hop | Possible | None |
| App sees real client IP | No (SNAT) | Yes |

* One-liner → Cluster spreads load evenly but hides the client IP | Local keeps the client IP but fails on nodes without Pods

### Which node should the user use?

* **NodePort doesn't answer that** → it opens the door everywhere and leaves the choice to someone else
* I have to hand out a node IP, or put something in front that knows all nodes (a load balancer)

### What happens when a node goes down

* Users pointing at **that node's IP** → requests time out → NodePort can't help → they must switch to another node's IP **manually**
* Users on other nodes → mostly fine → but Pods that lived on the dead node are gone too
* Timeline inside the cluster →
    * **0 s** → node stops, its kubelet stops sending heartbeats
    * **~40 s** → node controller marks it `NotReady` (`node-monitor-grace-period`) → its Pods marked not Ready → removed from every Service's endpoints → kube-proxy on healthy nodes updates rules
    * **0–40 s** → healthy nodes may still pick dead Pods → some requests hang or fail (the blip)
    * **~5 min** → Pods on the NotReady node evicted (default toleration 300 s) → ReplicaSet creates replacements on healthy nodes → added once Ready
* Routing heals in ~40 s | capacity heals in ~5 min
* NodePort address = a **node IP** → belongs to one machine → dies with it → Kubernetes can't move it → NodePort gives the port everywhere but **no single address that survives node failure**

### Ways to put one stable address in front

| Option | Where | How |
|---|---|---|
| **LoadBalancer Service** | Cloud (AWS/GCP/Azure) | Cloud LB with health checks → all nodes' NodePort |
| External LB (HAProxy / nginx VM) | On-prem | Configured with all node IPs + NodePort + health checks |
| **MetalLB** | Bare metal / on-prem / kind | Gives LoadBalancer Services a real IP that moves to a healthy node |
| DNS with all node IPs | Cheap hack | 3 A records → clients may still try the dead IP, caching slows recovery |

### When NodePort is used

* Labs, testing, quick demos, some on-prem setups
* Not exposed directly to users in production → ugly ports, users would need node IPs, no failover
* Still used **underneath** → a LoadBalancer Service sends traffic to NodePorts

### Simulate a node failure on kind

```bash
kubectl get pods -o wide                       # which Pods are on <worker>
docker stop <worker-node-container>            # "kill" the node
kubectl get nodes -w                           # NotReady after ~40 s
kubectl describe svc frontend-svc              # Endpoints shrink
docker start <worker-node-container>           # bring it back
```

## Reaching NodePort on kind (`extraPortMappings`)

### The problem

* Each kind node = a Docker container → NodePort opens 31000 **inside** each container
* **macOS / Windows** → Docker runs inside a hidden Linux VM (Docker Desktop) → the `172.18.0.x` node network exists only inside that VM → laptop can't reach `172.18.0.x:31000`
* **Native Linux** (e.g. Ubuntu) → Docker runs on my own kernel → the bridge network is on my machine → `curl 172.18.0.x:31000` works directly
* `localhost:31000` → on **any** OS, nothing on my laptop listens on 31000 unless I map it

### The fix → a pipe from my laptop into a node

```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
    image: kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5
    extraPortMappings:
      - containerPort: 31000   # port inside the node container → must equal the Service's nodePort
        hostPort: 31000        # port on my laptop
  - role: worker
    image: kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5
  - role: worker
    image: kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5
```

* `extraPortMappings` = kind passing Docker's `-p hostPort:containerPort` when it creates the node container → same as `docker run -p 31000:31000 ...`
* **hostPort** → outside end of the pipe (my laptop) | **containerPort** → inside end (the node)
* `containerPort` **must equal** the Service's `nodePort` → otherwise the pipe ends at a closed door
* `hostPort` can be anything → `hostPort: 9090` → open `localhost:9090` → still reaches `containerPort: 31000`
* Only the **control-plane** has the mapping → enough, NodePort opens 31000 on every node and forwards to Pods on workers
* Only **mapped** ports reach the cluster through `localhost` → a Service on nodePort `30950` is **not** reachable at `localhost:30950` unless 30950 is also mapped
* This is why the nodePort is fixed in the Service YAML (`nodePort: 31000`) instead of letting Kubernetes pick one
* `image: ...@sha256:...` → pins the exact Kubernetes version, the digest guarantees the identical image every time

### Can only be set at creation

* `extraPortMappings` can't be added to a running cluster → delete and recreate:

```bash
kind get clusters
kind delete cluster --name my-first-cluster
kind create cluster --name my-second-cluster --config kind-cluster.yaml
```

### The full chain

```
Browser ─▶ localhost:31000                          (laptop)
   ─▶ Docker port forward ─▶ control-plane container:31000
   ─▶ kube-proxy NodePort rule ─▶ frontend-svc
   ─▶ DNAT to an nginx Pod:80 (CNI delivers it if the Pod is on a worker)
```

## Lab: expose the frontend, hide the backend

* Real pattern → **frontend = NodePort** (outside door) | **backend = ClusterIP** (internal only, safer)

```
User ─▶ any node:31000 (frontend-svc, NodePort) ─▶ nginx Pod:80
                                                     │
                     backend-svc:9090 (ClusterIP) ◀──┘
                              │
                              └─▶ http-echo Pod:5678
```

```yaml
# frontend.yaml (Service part)
apiVersion: v1
kind: Service
metadata:
  name: frontend-svc
spec:
  type: NodePort
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80        # nginx's port, NOT the backend's 5678
      nodePort: 31000
  selector:
    app: frontend
```

```bash
kubectl apply -f backend.yaml
kubectl apply -f frontend.yaml
kubectl get all

kubectl get nodes -o wide                          # INTERNAL-IP column → 172.18.0.x
curl 172.18.0.2:31000                              # any node works (native Linux)
curl localhost:31000                               # through extraPortMappings
kubectl exec -it deploy/frontend-deploy -- curl backend-svc:9090   # backend from inside only
```

* Expected →
    * `localhost:31000` → **"Welcome to nginx!"** page
    * backend reachable only from inside → `Hello from backend :)`
* Plain nginx **doesn't call the backend** → it just serves its own page → the diagram's nginx → backend arrow shows the idea; making nginx forward needs a `proxy_pass http://backend-svc:9090;` config
* Moving the outside door from one Service to another → delete the old NodePort Service first → `nodePort: 31000` can belong to only one Service, and changing a Service's type in place keeps its old nodePort

### Reading `kubectl get all`

* `pod/...` → individual Pods
* `service/...` → `PORT(S)` = `port:nodePort/TCP` for NodePort | `port/TCP` for ClusterIP
* `deployment.apps/...` → `READY 3/3` = 3 of 3 desired Pods Ready
* `replicaset.apps/...` → created by the Deployment to keep the Pods running → hash in the name (`79f94c6cdc`) changes whenever the Pod template changes (that's how rollouts work)
* `ContainerCreating` for a while → image still downloading → becomes `Running`

## LoadBalancer

### The problem left by NodePort

* Users must know a node IP | node dies → its users are cut off | ugly ports like `:31000`

### What it does

* Asks the **cloud** (AWS, GCP, Azure) → "create a real load balancer with one external address and point it at all my nodes"

```
User ─▶ one external address (cloud LB)
          ─▶ health-checks every node
          ─▶ sends traffic only to healthy nodes on the NodePort
          ─▶ Service ─▶ Pod
```

* User only knows **one address** (e.g. `abc123.elb.amazonaws.com`) → normal ports like 80/443 → dead node skipped automatically
* Analogy → **main gate with a guard** outside the building → visitors only go to the gate → guard sends them through a working floor door
* A LoadBalancer Service gets **all three** → ClusterIP + NodePort + external address

```yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend-lb
spec:
  type: LoadBalancer
  ports:
    - protocol: TCP
      port: 80              # port on the load balancer AND the ClusterIP
      targetPort: 80        # nginx's port
      # nodePort: 31000     # optional → usually left out, Kubernetes picks one
  selector:
    app: frontend
```

### What happens when it's applied

1. API server stores it → assigns a **ClusterIP** and a **NodePort** (random, e.g. 32145)
2. kube-proxy writes ClusterIP + NodePort rules on every node → same as before
3. **cloud-controller-manager** (control-plane component that talks to the cloud API) sees `type: LoadBalancer` → calls the cloud → "create a load balancer"
4. Cloud creates it (on AWS an **ELB**) with →
    * **listener** on port 80
    * **targets** → every node on port 32145 (the NodePort)
    * **health checks** on each node
5. Cloud returns the address → written into the Service's status → `EXTERNAL-IP` column

```
NAME          TYPE           CLUSTER-IP    EXTERNAL-IP                PORT(S)
frontend-lb   LoadBalancer   10.96.80.12   abc123.elb.amazonaws.com   80:32145/TCP
```

* `80:32145` → LB/Service port : NodePort

### The packet path

```
User ─▶ abc123.elb.amazonaws.com:80
   ─▶ cloud LB picks a healthy node ─▶ node:32145 (NodePort)
   ─▶ kube-proxy iptables ─▶ DNAT ─▶ nginx Pod:80
```

* Node fails health checks → LB removes it within seconds → the failover NodePort couldn't give

### On AWS (EKS)

* Plain `type: LoadBalancer` → Classic LB by default, NLB with annotations
* Most teams install the **AWS Load Balancer Controller** →
    * `type: LoadBalancer` Service → **NLB** (L4)
    * **Ingress** → **ALB** (L7)
    * can target **Pod IPs directly** (`target-type: ip`) → skips the NodePort hop
* Internal LB (annotation) → private LB reachable only inside the VPC

### On kind

* No cloud → nobody creates the LB → `EXTERNAL-IP` stays `<pending>` forever → **normal, not a bug**

```bash
kubectl expose deployment frontend-deploy --name=frontend-lb --type=LoadBalancer --port=80
kubectl get svc frontend-lb          # EXTERNAL-IP <pending>
```

* To get a real IP locally → something must act like a cloud →
    * **cloud-provider-kind** → official Kubernetes SIG tool built for this
    * **MetalLB** → common for bare-metal and on-prem clusters

### Is it used in production?

* **Rare** → one LoadBalancer Service **per app** →
    * cost → one cloud LB each (roughly $16–20/month each on AWS before traffic)
    * many external addresses to manage
    * L4 only → can't route by URL path or hostname, no central TLS
* Normal web apps → **Ingress** (or Gateway API) → one entry point routes by path/host → app Services stay **ClusterIP**

```
app.com/       → frontend-svc (ClusterIP)
app.com/api    → api-svc      (ClusterIP)
admin.app.com  → admin-svc    (ClusterIP)
```

* **Still used** in production for →
    1. **In front of the Ingress controller** → ingress-nginx is just Pods → one `type: LoadBalancer` Service brings outside traffic to them → LB used **once**, at the edge
    2. **Non-HTTP traffic** → Ingress understands only HTTP/HTTPS → databases, MQTT, game servers, DNS, some gRPC → LoadBalancer Service
    3. **Internal load balancers** → expose a service privately inside the VPC (other clusters, VMs, VPN users)

| Situation | What's used |
|---|---|
| Normal web apps | ClusterIP + Ingress / Gateway API |
| Getting traffic into the Ingress controller | 1 LoadBalancer Service |
| TCP/UDP apps | LoadBalancer Service |
| Private access inside the VPC | Internal LoadBalancer Service |
| Labs and testing | NodePort |

## ExternalName

### The problem

* App inside the cluster needs something **outside** → e.g. a database on AWS RDS → `mydb.abc123.ap-south-1.rds.amazonaws.com`
* Hard-coded in the app → DB moves (test → prod, new instance) → change and redeploy the app

### What it does

* Creates a **nickname** inside the cluster → `my-db` → the long outside name
* App connects to `my-db` → DB changes → update only the Service → app untouched
* Analogy → saved phone contact "Papa" → number changes → update the contact once, keep tapping "Papa" | or speed-dial 111 for IT support

```yaml
apiVersion: v1
kind: Service
metadata:
  name: cka-db-svc
spec:
  type: ExternalName
  externalName: cka-db.judhtdmxwly6.us-east-1.rds.amazonaws.com   # RDS DNS name
```

* **No selector, no ports, no ClusterIP** → just `type` + `externalName`

| | ClusterIP / NodePort / LoadBalancer | ExternalName |
|---|---|---|
| Points to | Pods inside the cluster | A DNS name **outside** the cluster |
| Selector | Yes | No |
| Virtual IP | Yes | No |
| Endpoints / kube-proxy rules | Yes | No |
| Traffic flows through it | Yes (address rewrite) | No (only the name is swapped) |

### What actually happens

1. Applied → API server stores it → **no ClusterIP, no endpoints, no iptables rules**
2. CoreDNS creates a **CNAME** record (DNS alias) →
   `cka-db-svc.default.svc.cluster.local → CNAME → cka-db.judhtdmxwly6.us-east-1.rds.amazonaws.com`
3. App connects to `cka-db-svc:3306` →
    * asks CoreDNS → "that's another name for the RDS hostname"
    * resolution continues → RDS hostname → real IP (e.g. `10.0.5.23`)
    * app connects **directly** to `10.0.5.23:3306`
* Kubernetes is involved only in the **DNS step** → no DNAT, no load balancing

### Watch out

* **Ports are ignored** → app must use the outside service's real port (3306 for MySQL) → ExternalName can't map 80 → 3306
* **Must be a DNS name, not an IP** → `externalName: 10.0.5.23` → creates a CNAME to "10.0.5.23" → wrong
    * fixed outside **IP** → use a Service with **no selector** + an EndpointSlice I write by hand with that IP
* **HTTP/HTTPS can break** → HTTP sends `Host: cka-db-svc` | HTTPS certificate is for the real hostname, not the alias → many websites and APIs reject it → best for **databases and plain TCP**, risky for HTTPS APIs

### Real uses

* Short in-cluster name for a **managed database** (RDS, Cloud SQL)
* **Migrations** → `my-db` → outside DB today → later move the DB into the cluster and turn `my-db` into a normal ClusterIP Service → app never changes
* **Per-environment config** → `my-db` in the dev namespace → dev DB | in prod namespace → prod DB → same app YAML everywhere
* **Cross-namespace alias** → `my-db` → `postgres.database.svc.cluster.local`
* Third-party APIs and legacy systems (watch the HTTPS caveat)

### Try it

```bash
kubectl create service externalname my-google --external-name www.google.com
kubectl get svc my-google                                  # EXTERNAL-IP = www.google.com, no CLUSTER-IP
kubectl run test --rm -it --image=busybox -- nslookup my-google
# my-google.default.svc.cluster.local  canonical name = www.google.com → then Google's IPs
```

## Headless Services

* `clusterIP: None` → no virtual IP, no load balancing
* DNS returns **every Pod's IP** directly instead of one Service IP
* Used with **StatefulSets** (databases) → client must reach a specific Pod → `mysql-0.mysql.default.svc.cluster.local` (e.g. the primary), not "any free one"

```yaml
spec:
  clusterIP: None
  selector:
    app: mysql
  ports:
    - port: 3306
```

## Which type when

| Need | Use |
|---|---|
| Pod-to-Pod traffic inside the cluster | ClusterIP |
| Quick access from outside in a lab | NodePort |
| Public endpoint on a cloud (TCP/UDP, or for the Ingress controller) | LoadBalancer |
| Many HTTP apps behind one entry point | ClusterIP + Ingress / Gateway API |
| Short name for an outside DNS name | ExternalName |
| Reach individual Pods (StatefulSets) | Headless |

## Request flow summary

```
ClusterIP     Pod ─▶ svc-name:port ─▶ (DNS → ClusterIP) ─▶ iptables DNAT ─▶ Pod:targetPort

NodePort      User ─▶ anyNodeIP:nodePort ─▶ ClusterIP:port ─▶ Pod:targetPort
              (node down → user must switch to another node IP manually)

LoadBalancer  User ─▶ LB address:port ─▶ healthy node:nodePort ─▶ ClusterIP:port ─▶ Pod:targetPort

ExternalName  Pod ─▶ svc-name ─▶ (DNS CNAME) ─▶ outside hostname ─▶ connects directly
```

!!! tip "Quick revision"

    * Service = stable virtual IP + DNS name + load balancing in front of Pods with changing IPs
    * Finds Pods by label selector → only Ready Pods, same namespace → list kept in EndpointSlices
    * `port` = Service's port (callers) | `targetPort` = app's port in the Pod | `nodePort` = port on every node (30000–32767)
    * ClusterIP is virtual → kube-proxy writes iptables DNAT rules on every node → conntrack reverses them for replies
    * CoreDNS maps `svc.namespace.svc.cluster.local` → ClusterIP | Pods use it via `/etc/resolv.conf` (`10.96.0.10`)
    * LoadBalancer ⊃ NodePort ⊃ ClusterIP | ExternalName = CNAME only | Headless = Pod IPs from DNS
    * Wrong `targetPort` → Pods Running, Endpoints filled, but connection refused / empty response

!!! question "Interview points"

    * Why do we need Services? → Pod IPs change on every restart, so a Service gives a stable IP and DNS name and load-balances across the current Ready Pods
    * How does a Service know which Pods to send traffic to? → its label selector; the EndpointSlice controller keeps a list of Ready Pods with matching labels in the same namespace
    * port vs targetPort vs nodePort? → port is the Service's port that callers use, targetPort is the port the app in the Pod listens on, nodePort is the port opened on every node for outside traffic
    * Is the ClusterIP assigned to any interface? → no, it's virtual; kube-proxy programs iptables/IPVS/nftables rules on every node that DNAT it to a Pod IP
    * Who does the load balancing for a ClusterIP Service? → kube-proxy's rules in the node kernel, choosing a random endpoint per new connection; no proxy process sits in the data path in iptables mode
    * What does CoreDNS do for Services? → watches the API server and answers name lookups, mapping service names to ClusterIPs, or to a CNAME for ExternalName
    * Pods are Running but the Service's Endpoints are empty, why? → the selector doesn't match the Pod labels, the Pods aren't Ready, or they're in another namespace
    * Endpoints are filled but requests get connection refused? → targetPort doesn't match the port the app actually listens on
    * Does a NodePort Service also have a ClusterIP? → yes, NodePort builds on ClusterIP and LoadBalancer builds on NodePort
    * Default NodePort range? → 30000–32767
    * What happens with NodePort if a node goes down? → clients using that node's IP fail and must switch manually; inside the cluster its Pods are removed from endpoints after the node goes NotReady (~40 s) and replaced after eviction (~5 min)
    * externalTrafficPolicy Cluster vs Local? → Cluster forwards to Pods on any node but SNATs and hides the client IP; Local only uses Pods on the receiving node and preserves the client IP
    * Who creates the cloud load balancer for a LoadBalancer Service? → the cloud-controller-manager, through the cloud provider's API
    * Why is EXTERNAL-IP pending on kind or bare metal? → there's no cloud controller to provision a load balancer; use MetalLB or cloud-provider-kind
    * Why not one LoadBalancer per app in production? → cost and no L7 routing; use one LoadBalancer for the ingress controller and ClusterIP Services behind Ingress
    * What is an ExternalName Service? → a DNS CNAME alias to an external hostname with no ClusterIP, selector or proxying
    * What is a headless Service? → clusterIP: None, DNS returns the individual Pod IPs, used with StatefulSets
    * Why does kind need extraPortMappings? → nodes are Docker containers, so the host port must be mapped into a node container to reach a NodePort via localhost; it can only be set at cluster creation
