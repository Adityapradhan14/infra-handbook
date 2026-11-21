# Namespaces

## The problem

* One cluster, many teams / apps / environments → without separation it's one flat pile:
    * Two teams can't both have a Service called `backend-svc` → names must be unique
    * `kubectl get pods` shows everyone's Pods
    * No clean way to give a team access to **only its own** stuff, or cap how much CPU/memory it uses
* Running a separate cluster per team or app → expensive and a lot to operate

## What a namespace is

* A **logical partition inside one cluster** → a folder that groups resources
* Names only need to be unique **within** a namespace → `team-a/backend-svc` and `team-b/backend-svc` can both exist
* Analogy → a big house shared by 4 families → without rooms there's no privacy or order → give each family a room
    * house = cluster | families = apps / teams | rooms = namespaces
* Not the same as **Linux namespaces** (process isolation for containers, see [Container Runtime Internals](container-runtime.md)) → same word, different idea

## Why use them

* **Organisation** → group related resources by team, app or environment → manage them together
* **No naming conflicts** → same names in different namespaces
* **Access control** → RBAC Roles and RoleBindings are per namespace → a developer gets `dev` only
* **Resource limits** → ResourceQuota and LimitRange are per namespace
* **Network rules** → NetworkPolicies are written per namespace
* **Multi-tenancy** → many apps / teams on one cluster
* **Bulk cleanup** → delete the namespace → everything inside goes with it

## Built-in namespaces

```bash
kubectl get namespaces        # or: kubectl get ns
```

| Namespace | Holds |
|---|---|
| `default` | My stuff when I don't say otherwise → lets a new cluster be used without creating a namespace |
| `kube-system` | Objects created by Kubernetes itself → CoreDNS, kube-proxy, and on kind/kubeadm the control-plane Pods (apiserver, etcd, scheduler, controller-manager) |
| `kube-public` | Readable by everyone, even unauthenticated → mostly the `cluster-info` ConfigMap, almost empty |
| `kube-node-lease` | One **Lease** object per node → node heartbeats the control plane uses to judge node health |
| `local-path-storage` | **kind only** → the Local Path Provisioner that backs PersistentVolumes |

## Namespaced vs cluster-scoped

* Not every resource lives in a namespace

| Namespaced | Cluster-scoped (no namespace) |
|---|---|
| Pods, Deployments, ReplicaSets, Services, ConfigMaps, Secrets, PVCs, Roles, RoleBindings, ServiceAccounts, Ingress, NetworkPolicies, ResourceQuotas | Nodes, Namespaces themselves, PersistentVolumes, StorageClasses, ClusterRoles, ClusterRoleBindings, CRDs |

```bash
kubectl api-resources --namespaced=true
kubectl api-resources --namespaced=false
```

* `-n` on a cluster-scoped resource is ignored → `kubectl get nodes -n dev` still lists every node
* Namespaces **can't be nested** → one level only

## Creating, listing, deleting

### Imperative

```bash
kubectl create namespace app1-ns          # or: kubectl create ns app1-ns
```

### Declarative

```yaml
# app1-ns.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: app1-ns
```

```bash
kubectl apply -f app1-ns.yaml
```

* Generate it instead of typing → `kubectl create ns app1-ns --dry-run=client -o yaml > app1-ns.yaml`
* Name rules → lowercase letters, numbers, `-` | max 63 chars | can't start with `kube-` (reserved)

### List and inspect

```bash
kubectl get ns
kubectl describe ns app1-ns               # labels, status, quotas and limits applied
```

### Delete

```bash
kubectl delete namespace app1-ns
```

* Deletes the namespace **and everything inside it** → Pods, Services, ConfigMaps, Secrets, PVCs… → no undo, no confirmation prompt
* Namespace shows **`Terminating`** while its contents are removed → stuck in Terminating for long = some object has a **finalizer** that can't complete (often a CRD whose controller is gone) → find it with `kubectl api-resources --verbs=list --namespaced -o name | xargs -n1 kubectl get -n app1-ns --ignore-not-found`
* `default`, `kube-system`, `kube-public`, `kube-node-lease` can't be deleted

## The `-n` and `-A` flags

| Flag | Meaning |
|---|---|
| `-n <ns>` / `--namespace <ns>` | Run the command in that namespace |
| `-A` / `--all-namespaces` | Run it across every namespace → adds a NAMESPACE column |
| *(neither)* | The namespace set in the current context → `default` unless changed |

```bash
kubectl get pods -n app1-ns
kubectl get services -A
kubectl get all -n kube-system
```

* Every namespaced command is scoped to **one** namespace → that's why `kubectl get pods` showed only my app, while `-n kube-system` showed CoreDNS, kube-proxy and the rest
* `NotFound` on something I know exists → first suspect → **wrong namespace**

## Deploying into a namespace

### Way 1 → `-n` at apply time

```bash
kubectl create ns app1-ns
kubectl apply -f frontend-deploy.yaml -n app1-ns
kubectl apply -f backend-deploy.yaml -n app1-ns
kubectl get all -n app1-ns
```

* Same YAML files as in [Imperative Commands](imperative-commands.md) → no change to the files → the objects just land in `app1-ns`
* Can apply the same files to `default` **and** `app1-ns` → two independent copies, same names

### Way 2 → `namespace` in the manifest

```yaml
metadata:
  name: backend-deploy
  namespace: app1-ns
```

* Better for real setups → the file says where it belongs → no relying on someone remembering `-n`
* Conflict → file says `app1-ns`, command says `-n dev` → error: `the namespace from the provided object "app1-ns" does not match the namespace "dev"`
* The namespace must exist first → otherwise `namespaces "app1-ns" not found` → put the Namespace object first in the file (or a `00-namespace.yaml`)

### The Service and its Pods

* A Service's selector only matches Pods in **its own namespace** → backend-svc in `app1-ns` never sends traffic to backend Pods in `default`

## DNS across namespaces

### Test it

From a test Pod in `default` (with backend running only in `app1-ns`):

```bash
kubectl run test-pod --image=busybox -it --rm --restart=Never -- /bin/sh
# wget -qO- backend-svc:9090             ✗ bad address 'backend-svc'
# wget -qO- backend-svc.app1-ns:9090     ✓ Hello from Backend
```

From a test Pod in `app1-ns`:

```bash
kubectl run test-pod -n app1-ns --image=busybox -it --rm --restart=Never -- /bin/sh
# wget -qO- backend-svc:9090             ✓ Hello from Backend
```

* busybox has **no `curl`** → use `wget -qO-` (or an image with curl → `nginx`, `curlimages/curl`, `nicolaka/netshoot`)

### Why → the search domains

```bash
# cat /etc/resolv.conf   (Pod in app1-ns)
search app1-ns.svc.cluster.local svc.cluster.local cluster.local
nameserver 10.96.0.10
options ndots:5
```

* The **first search domain is the Pod's own namespace** → short name `backend-svc` becomes `backend-svc.app1-ns.svc.cluster.local`
* From `default` the first try is `backend-svc.default.svc.cluster.local` → doesn't exist → the remaining search domains don't form a valid Service name either → `bad address`
* `backend-svc.app1-ns` → second search domain turns it into `backend-svc.app1-ns.svc.cluster.local` → works

### Name formats

| Called from | Name |
|---|---|
| Same namespace | `backend-svc` |
| Other namespace | `backend-svc.app1-ns` |
| Anywhere (FQDN) | `backend-svc.app1-ns.svc.cluster.local` |

```
<service-name>.<namespace>:<service-port>      →  backend-svc.app1-ns:9090
```

* The port is the **Service port** (9090), not the container port (5678)
* Gotcha → if `default` **also** has a `backend-svc` (left from an earlier lab), the short name from `default` succeeds → it silently hits the **default** copy → when testing isolation, check `kubectl get svc -A` first
* In app config → prefer `<svc>.<ns>` or the FQDN for anything crossing namespaces → never rely on the caller's namespace

## Namespaces are not isolation (by default)

* Namespaces separate **names and management** → **not the network**
* A Pod in `dev` can reach a Service in `prod` → `backend-svc.prod` → by default nothing stops it
* Pod IPs are one flat network across all namespaces (CNI job)
* Real isolation = namespaces **plus**:
    * **NetworkPolicy** → allow / deny traffic between Pods and namespaces → needs a CNI that enforces it (Calico, Cilium) → kind's default **kindnet ignores** NetworkPolicies
    * **RBAC** → who can read / change what, per namespace
    * **ResourceQuota / LimitRange** → stop one namespace starving the others
    * **Pod Security Admission** → namespace labels that block privileged Pods
* Strong isolation for untrusted tenants or prod → often **separate clusters**, not just namespaces

## Setting a default namespace

* Typing `-n app1-ns` on every command is tiring → store it in the **context** (see [kind, kubeconfig & Contexts](kind-and-kubeconfig.md#contexts))

```bash
kubectl config set-context --current --namespace=app1-ns
kubectl config view --minify | grep namespace        # namespace: app1-ns
kubectl config get-contexts                          # NAMESPACE column
kubectl get pods                                     # now app1-ns Pods
kubectl config set-context --current --namespace=default    # switch back
```

* It's saved in `~/.kube/config` → stays after closing the terminal → easy to forget → run a delete in the wrong namespace
* kubectl doesn't check the namespace exists → a typo in the name = every command returns "No resources found"
* Typo in the flag (`--namepsace`) → `error: unknown flag` → read the flag name
* Habit → show the current context and namespace in the shell prompt (`kube-ps1`), or use `kubens` (from `kubectx`) to switch

## ResourceQuota and LimitRange (first look)

* **ResourceQuota** → cap on the **total** a namespace can use

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: app1-quota
  namespace: app1-ns
spec:
  hard:
    pods: "10"
    requests.cpu: "2"
    requests.memory: 2Gi
    limits.cpu: "4"
    limits.memory: 4Gi
```

* Once a CPU/memory quota exists → every new Pod **must** set requests/limits, or it's rejected
* **LimitRange** → defaults and min/max **per Pod or container** in the namespace → fills in requests/limits for Pods that don't set them

```bash
kubectl describe ns app1-ns        # shows quota used / hard and the limit ranges
kubectl get resourcequota -n app1-ns
```

## How they're used in real setups

* **Per environment** → `dev`, `staging`, `prod` → prod often on its own cluster instead
* **Per team or app** → `payments`, `search`, `checkout`
* **Per tool** → `argocd`, `monitoring` (Prometheus, Grafana), `ingress-nginx`, `cert-manager` → Helm charts usually install into their own namespace (`helm install ... -n monitoring --create-namespace`)
* Naming → clear and consistent → `team-app-env` style, e.g. `payments-api-prod`
* Label namespaces (`team=payments`, `env=prod`) → NetworkPolicies and tools can select by them
* Every manifest carries `metadata.namespace` → the namespace object is in Git too

## Lab: same app, two namespaces

```bash
kubectl create ns app1-ns
kubectl apply -f backend-deploy.yaml -f frontend-deploy.yaml -n app1-ns
kubectl get all -n app1-ns
kubectl get svc -A | grep -e backend -e frontend     # any copies left in default?

# from default
kubectl run t1 --rm -it --restart=Never --image=busybox -- wget -qO- backend-svc.app1-ns:9090

# from inside app1-ns
kubectl run t2 -n app1-ns --rm -it --restart=Never --image=busybox -- wget -qO- backend-svc:9090

# default namespace in the context
kubectl config set-context --current --namespace=app1-ns
kubectl get pods
kubectl config set-context --current --namespace=default

# cleanup → everything inside goes too
kubectl delete ns app1-ns
kubectl get ns
```

!!! tip "Quick revision"

    * Namespace = logical partition inside one cluster → names unique per namespace, not per cluster
    * Built-ins → `default`, `kube-system`, `kube-public`, `kube-node-lease` (+ `local-path-storage` on kind)
    * Namespaced → Pods, Deployments, Services, ConfigMaps, Secrets, PVCs, Roles | cluster-scoped → Nodes, PVs, StorageClasses, ClusterRoles, Namespaces
    * `-n <ns>` = one namespace | `-A` = all | neither = the context's namespace
    * `kubectl delete ns` deletes everything inside, no prompt → stuck `Terminating` = finalizer
    * Cross-namespace DNS → `<svc>.<ns>:<service-port>` | short name works only in the same namespace because of the `search` line
    * Namespaces don't isolate the network → NetworkPolicy (with a CNI that enforces it) + RBAC + quotas do
    * Default namespace → `kubectl config set-context --current --namespace=<ns>` → saved in kubeconfig

!!! question "Interview points"

    * What is a namespace in Kubernetes? → a logical partition of one cluster that scopes resource names and is the unit for RBAC, resource quotas and network policies
    * Do namespaces provide network isolation? → no, Pods in any namespace can reach each other by default; isolation needs NetworkPolicies enforced by the CNI, plus RBAC and quotas
    * How does a Pod reach a Service in another namespace? → service.namespace or service.namespace.svc.cluster.local on the Service port
    * Why does the short Service name only work in the same namespace? → the Pod's resolv.conf search list starts with its own namespace.svc.cluster.local
    * Which resources are not namespaced? → Nodes, PersistentVolumes, StorageClasses, ClusterRoles, ClusterRoleBindings, CRDs and Namespaces themselves
    * What are the default namespaces? → default, kube-system, kube-public and kube-node-lease
    * What is kube-node-lease for? → it holds a Lease per node that the kubelet renews as a lightweight heartbeat for node health
    * What happens when you delete a namespace? → every namespaced object inside it is deleted; it stays Terminating until finalizers complete
    * Why is a namespace stuck in Terminating? → a resource inside has a finalizer whose controller can't finish, often a CRD whose operator was removed
    * How do you change the default namespace for kubectl? → kubectl config set-context --current --namespace=name, which is saved in the kubeconfig context
    * Can a Service select Pods in another namespace? → no, a Service selector only matches Pods in its own namespace
    * What do ResourceQuota and LimitRange do? → ResourceQuota caps the total resources and object counts of a namespace; LimitRange sets default and min/max requests and limits per Pod or container
    * Namespaces or separate clusters for prod? → namespaces are cheap soft isolation within one control plane; separate clusters give a hard boundary for blast radius, security and upgrades
