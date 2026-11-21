# Imperative Commands

## Why learn them at all

* Real clusters are run **declaratively** → YAML in Git → applied by CI/CD or GitOps (Argo CD, Flux), often templated with Helm/Kustomize → nobody runs production with `kubectl create`
* Imperative commands are still used every day, for 3 jobs:
    * **Generate YAML** → let kubectl write the skeleton, edit it, `apply` it (see [YAML, Manifests & Objects](yaml-and-manifests.md#generate-yaml-instead-of-writing-it))
    * **CKA / CKAD exam** → timed → typing a full manifest from memory wastes minutes
    * **Troubleshooting** → throwaway test Pods, `port-forward`, `logs`, `exec`, `rollout restart`, `scale` during an incident
* Rule → **imperative to generate and debug, declarative to run**

## The dry-run flags

| Flag | What happens | Use it for |
|---|---|---|
| `--dry-run=client` | kubectl builds the object locally, nothing is created | Getting a YAML skeleton fast |
| `--dry-run=server` | Sent to the API server → schema + admission checks (quotas, policies, webhooks) → then thrown away | "Would this actually be accepted?" before a real apply |
| `-o yaml` | Print the object as YAML instead of creating it | Always paired with a dry-run here |

* Catch → `client` doesn't always mean "no API call" → `kubectl expose` still **reads** the live Deployment to copy its selector → the Deployment must already exist, or → `Error from server (NotFound): deployments.apps "backend-deploy" not found`

## `>` vs `>>`

* `> file.yaml` → create / **overwrite** the file
* `>> file.yaml` → **append** to the end of the file
* Appending a second object needs a **`---`** separator between them → without it the file is one YAML document with duplicate keys (`apiVersion`, `kind`, `metadata`…) → `apply` errors or silently keeps only one object
* `--dry-run=client -o yaml` does **not** print a leading `---` → add it myself:

```bash
echo '---' >> backend-deploy.yaml
kubectl expose ... --dry-run=client -o yaml >> backend-deploy.yaml
```

* Forgot it? Fix in place → the Service starts with `apiVersion: v1`, the Deployment with `apps/v1`, so this match is unique:

```bash
sed -i 's/^apiVersion: v1$/---\napiVersion: v1/' backend-deploy.yaml
grep -n -e '^---' -e '^kind' backend-deploy.yaml      # Deployment, ---, Service
```

## Backend: Deployment + ClusterIP Service

### Step 1 → Deployment

```bash
kubectl create deployment backend-deploy \
  --image=hashicorp/http-echo \
  --replicas=3 \
  --port=5678 \
  --dry-run=client -o yaml > backend-deploy.yaml
```

| Flag | Meaning |
|---|---|
| `backend-deploy` | Deployment name → also becomes the Pod label `app: backend-deploy` |
| `--image` | Container image → `hashicorp/http-echo` = tiny web server that replies with fixed text |
| `--replicas=3` | 3 Pods |
| `--port=5678` | Writes `containerPort: 5678` into the Pod template |

### What `--port` / `containerPort` really does

* It **only writes** `containerPort: 5678` into the YAML → mostly **documentation**
* It does **not** →
    * make the app listen on 5678 → the **app** decides that (http-echo listens on 5678 by default)
    * expose anything outside the Pod
    * block other ports → a port not listed is still reachable inside the cluster
* Where it does matter →
    * `kubectl expose` without `--target-port` → copies `containerPort` into the Service's `targetPort` → no `containerPort` and no flag → expose fails ("couldn't find port via --port flag or introspection")
    * **Named ports** → `containerPort: 5678` + `name: http` → Service uses `targetPort: http` → change the number in one place only
    * Probes can point at the named port
* Proof it's informational → `kubectl port-forward deploy/backend-deploy 8080:5678` works even with `containerPort` deleted
* Mental model → **app** = the port actually listened on | **containerPort** = a label on it | **Service** = what exposes it

### Generated YAML, cleaned up

* Dry-run output has empty noise → `strategy: {}`, `resources: {}`, `status: {}`, `creationTimestamp: null` → delete them, Kubernetes fills defaults, and `status` is never mine to write
* Add `args` → http-echo needs `-text` to know what to reply → older versions exit with `Missing -text option` → CrashLoopBackOff

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-deploy
  labels:
    app: backend-deploy
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend-deploy        # must match the template labels
  template:
    metadata:
      labels:
        app: backend-deploy      # the Service selects on this too
    spec:
      containers:
      - name: http-echo
        image: hashicorp/http-echo
        args:
        - "-text=Hello from Backend"
        ports:
        - containerPort: 5678
```

### Step 2 → ClusterIP Service

```bash
kubectl apply -f backend-deploy.yaml              # expose needs the live Deployment
echo '---' >> backend-deploy.yaml
kubectl expose deployment backend-deploy \
  --type=ClusterIP \
  --port=9090 \
  --target-port=5678 \
  --name=backend-svc \
  --dry-run=client -o yaml >> backend-deploy.yaml
```

| Part | Meaning |
|---|---|
| `expose deployment backend-deploy` | Build a Service for this Deployment → copies its selector (`app: backend-deploy`) and labels |
| `--type=ClusterIP` | Internal-only virtual IP → the default, so optional |
| `--port=9090` | Port **the Service** listens on → callers use `backend-svc:9090` |
| `--target-port=5678` | Port **in the Pod** traffic is forwarded to → must match the app | omitted → falls back to `containerPort` |
| `--name=backend-svc` | Service name → also its DNS name | omitted → same name as the Deployment |

```yaml
---
apiVersion: v1
kind: Service
metadata:
  name: backend-svc
  labels:
    app: backend-deploy
spec:
  type: ClusterIP
  selector:
    app: backend-deploy
  ports:
  - port: 9090
    protocol: TCP
    targetPort: 5678
```

```
client Pod → backend-svc:9090 → (selector picks 1 of 3 Pods) → <pod-IP>:5678 → http-echo
```

### Step 3 → apply and verify

```bash
kubectl apply -f backend-deploy.yaml
# deployment.apps/backend-deploy unchanged     ← already exists, file matches → nothing to do
# service/backend-svc created
kubectl get deploy,svc,pods -l app=backend-deploy
kubectl get endpoints backend-svc               # 3 Pod IPs on :5678 → selector matches
```

* `unchanged` → `apply` compares file vs live object and only changes what differs → re-applying the same file is safe (idempotent)
* Empty endpoints → selector doesn't match Pod labels, or Pods not Ready (see [Debugging Services & DNS](debugging-services.md))

## Frontend: Deployment + NodePort Service

```bash
kubectl create deployment frontend-deploy \
  --image=nginx \
  --replicas=3 \
  --port=80 \
  --dry-run=client -o yaml > frontend-deploy.yaml
kubectl apply -f frontend-deploy.yaml
echo '---' >> frontend-deploy.yaml
kubectl expose deployment frontend-deploy \
  --type=NodePort \
  --port=80 \
  --target-port=80 \
  --name=frontend-svc \
  --dry-run=client -o yaml >> frontend-deploy.yaml
```

* `--type=NodePort` → opens the same port (30000–32767) on **every node** → reachable from outside via any node IP
* `kubectl expose` has **no `--node-port` flag** → Kubernetes picks a random port → to fix it, edit the YAML:

```yaml
spec:
  type: NodePort
  selector:
    app: frontend-deploy
  ports:
  - port: 80
    targetPort: 80
    nodePort: 31000        # added by hand
```

* Result in `kubectl get svc` → `80:31000/TCP` → read as **service port 80, node port 31000**

```
<any-node-IP>:31000 → frontend-svc:80 → nginx Pod :80
```

```bash
kubectl get nodes -o wide        # node INTERNAL-IPs (kind nodes = Docker containers, 172.18.0.x)
curl 172.18.0.2:31000            # from the laptop on native Linux → nginx welcome page
```

* `localhost:31000` only works if the kind cluster was created with `extraPortMappings` for it (see [Services](services.md#reaching-nodeport-on-kind-extraportmappings))

### The other way → `kubectl create service`

* `kubectl create service nodeport frontend-svc --tcp=80:80 --node-port=31000` → **does** accept a node port
* Catch → it sets the selector to `app: frontend-svc` (the **Service's** name) → doesn't match Pods labelled `app: frontend-deploy` → empty endpoints
* So → `expose` gets the selector right, `create service` gets the nodePort right → either way one manual edit

## Labels with imperative commands

* `kubectl create deployment X` → always labels the Pods `app=X` → **no flag** for custom Pod labels → edit `template.metadata.labels` **and** `selector.matchLabels` together in the YAML
* `kubectl label deployment X env=prod` → labels the **Deployment object**, not its Pods → the Pod template is untouched
* `kubectl run` (plain Pod) → takes labels directly:

```bash
kubectl run nginx-pod \
  --image=nginx \
  --restart=Never \
  --labels="app=nginx,env=production"       # comma-separated key=value
kubectl get pods --show-labels
kubectl get pods -l env=production          # filter by label
```

* Why labels matter → Services and Deployments find Pods **only** by labels → wrong label = no traffic, or a ReplicaSet that keeps creating Pods

### See it break

```bash
kubectl get pods -l app=backend-deploy
kubectl label pod <one-backend-pod> app=broken --overwrite
kubectl get endpoints backend-svc           # that Pod's IP drops out
kubectl get pods --show-labels              # ReplicaSet saw only 2 → created a 3rd
kubectl delete pod <the-broken-pod>         # cleanup → it's orphaned now
```

## Test Pods

### Generate a Pod manifest

```bash
kubectl run my-nginx \
  --image=nginx \
  --restart=Never \
  --labels=app=test-pod \
  --dry-run=client -o yaml > test-pod.yaml
```

### Throwaway Pod for troubleshooting

```bash
kubectl run test-pod \
  --rm -it \
  --restart=Never \
  --labels=app=test-pod \
  --image=nginx \
  -- /bin/sh
```

| Flag | Meaning |
|---|---|
| `--rm` | Delete the Pod as soon as I exit the shell → `pod "test-pod" deleted` |
| `-it` | Interactive + terminal → I get a shell prompt |
| `--restart=Never` | Plain Pod, not restarted if it exits → right for one-off checks |
| `-- /bin/sh` | Command to run instead of the image's default → everything after `--` goes to the container |

* Why a test Pod at all → a **ClusterIP** isn't reachable from the laptop → I must test from **inside** the cluster
* Image choice →
    * `nginx` → has `curl` → `curl backend-svc:9090`
    * `busybox` → **no curl** → use `wget -qO- backend-svc:9090` | has `nslookup`
    * `nicolaka/netshoot` → everything (curl, dig, nslookup, tcpdump) → best for network debugging
* One-shot, no shell:

```bash
kubectl run tmp --rm -it --restart=Never --image=busybox -- wget -qO- backend-svc:9090
```

* Newer kubectl prints → "All commands and output from this session will be recorded in container logs" → anything typed (including secrets) ends up in `kubectl logs` → don't paste credentials into test Pods

## What happened on `curl backend-svc:9090`

From inside the test Pod:

```bash
# curl backend-svc:9090
Hello from Backend
# cat /etc/resolv.conf
search default.svc.cluster.local svc.cluster.local cluster.local
nameserver 10.96.0.10
options ndots:5
```

```bash
kubectl get svc -n kube-system              # kube-dns  ClusterIP  10.96.0.10  53/UDP,53/TCP,9153/TCP
kubectl describe svc kube-dns -n kube-system   # Selector k8s-app=kube-dns → Endpoints 10.244.0.2:53, 10.244.0.3:53
kubectl get pods -n kube-system -o wide     # coredns-... Pods on exactly those IPs
```

1. `nameserver 10.96.0.10` → the Pod sends DNS queries here → it's the **kube-dns Service**
2. kube-dns is a normal ClusterIP Service → its endpoints are the 2 **CoreDNS** Pods → same label-selector mechanism as `backend-svc`, just in `kube-system`
3. `backend-svc` isn't a full name → resolver appends the `search` domains in order → first try `backend-svc.default.svc.cluster.local` → exists → done
4. CoreDNS answers with backend-svc's ClusterIP
5. **kube-proxy** (one Pod per node) has written rules on every node → ClusterIP:9090 → one of the 3 backend Pods on :5678

```
test Pod → CoreDNS (via kube-dns 10.96.0.10) → backend-svc = 10.96.x.x
        → 10.96.x.x:9090 → kube-proxy rules → backend Pod :5678 → "Hello from Backend"
```

* `ndots:5` → names with **fewer than 5 dots** try the search domains first → great for short in-cluster names | costs extra lookups for external names (`google.com` → 3 failed lookups first) → fix: query the FQDN with a trailing dot (`google.com.`) or lower `ndots` in the Pod's `dnsConfig`
* Short name works only in the **same namespace** → more in [Namespaces](namespaces.md#dns-across-namespaces)

## Imperative commands worth knowing

```bash
# generate
kubectl run <pod> --image=<img> --dry-run=client -o yaml > pod.yaml
kubectl create deployment <name> --image=<img> --replicas=3 --port=80 --dry-run=client -o yaml > deploy.yaml
kubectl expose deployment <name> --port=80 --target-port=8080 --dry-run=client -o yaml > svc.yaml
kubectl create configmap <name> --from-literal=key=value --dry-run=client -o yaml > cm.yaml
kubectl create secret generic <name> --from-file=./creds --dry-run=client -o yaml > secret.yaml
kubectl create namespace <name> --dry-run=client -o yaml > ns.yaml

# debug / operate
kubectl run tmp --rm -it --restart=Never --image=nicolaka/netshoot -- sh
kubectl port-forward deploy/<name> 8080:80
kubectl logs <pod> [-f] [--previous]
kubectl exec -it <pod> -- sh
kubectl scale deploy <name> --replicas=5
kubectl rollout restart deploy <name>
kubectl rollout undo deploy <name>
kubectl label pod <pod> key=value [--overwrite]
```

* After any imperative change to something that came from a file → update the file → otherwise file and cluster drift apart (see [last-applied-configuration](yaml-and-manifests.md#kubectl-apply-and-last-applied-configuration))
* Secrets in real setups → Sealed Secrets / External Secrets / Vault, not `create secret` by hand

## Cleanup

```bash
kubectl delete -f backend-deploy.yaml -f frontend-deploy.yaml
kubectl get all
```

* `delete -f` removes everything the file describes → no need to delete Deployment and Service one by one (and no `services "backend-deploy" not found` from guessing the wrong name)

!!! tip "Quick revision"

    * Imperative → generate YAML, exams, debugging | declarative YAML in Git → how real clusters run
    * `--dry-run=client` = build locally | `--dry-run=server` = full API validation, not saved | `-o yaml` = print it
    * `>` overwrites, `>>` appends → add `---` between objects
    * `kubectl expose` reads the live Deployment → apply the Deployment first
    * `--port` on `create deployment` = `containerPort` = documentation | the app decides the real port
    * Service `port` = what callers use | `targetPort` = the app's port in the Pod | `nodePort` set by editing YAML
    * `create deployment` labels Pods `app=<name>` only → custom labels by editing the YAML
    * Test Pod → `kubectl run tmp --rm -it --restart=Never --image=... -- sh` → ClusterIP is only reachable from inside
    * Pod DNS → `/etc/resolv.conf` → kube-dns Service → CoreDNS Pods → search domains make short names work

!!! question "Interview points"

    * Are imperative commands used in production? → not to manage workloads; production uses declarative manifests in Git applied by CI/CD or GitOps, while imperative commands are used to generate manifests and for debugging
    * --dry-run=client vs --dry-run=server? → client builds the object locally without creating it; server sends it to the API server for schema and admission validation but does not persist it
    * Does containerPort open or expose a port? → no, it is informational; the application decides which port it listens on and a Service exposes it, though kubectl expose and named ports use it
    * Why must the Deployment exist before kubectl expose, even with a client dry-run? → expose reads the live Deployment to copy its selector into the Service
    * How do you set a fixed nodePort when kubectl expose has no flag for it? → generate the YAML and add nodePort under ports, or use kubectl create service nodeport --node-port and fix its selector
    * Why put --- between objects in one file? → it separates YAML documents; without it the objects merge into one document with duplicate keys
    * How do you test a ClusterIP Service? → from a temporary Pod inside the cluster, e.g. kubectl run tmp --rm -it --restart=Never --image=busybox -- wget -qO- svc:port
    * How does a Pod resolve a short Service name? → /etc/resolv.conf points to the kube-dns Service (CoreDNS) and its search domains expand the name to service.namespace.svc.cluster.local
    * What does ndots:5 do and why can it hurt? → names with fewer than five dots try the search domains first, so external names cause several failed lookups before the real one
    * What happens if you change a Pod's label so it no longer matches? → it drops out of the Service endpoints and the ReplicaSet creates a replacement, leaving the relabelled Pod orphaned
