# kind, kubeconfig & Contexts

*Hands-on notes, CKA course Day 8, done on my own Ubuntu machine*

## What kind is

* `kind` = **K**ubernetes **in** **D**ocker → runs a whole Kubernetes cluster on my laptop
* Each **node** is a Docker container running the `kindest/node` image → inside it: systemd, kubelet, containerd, and the control-plane Pods
* Free, starts in about a minute, safe to break and delete → perfect for learning and labs
* Other local options → minikube, k3d | real clusters → `kubeadm`, EKS, GKE, AKS
* Install docs → [kubectl](https://kubernetes.io/docs/tasks/tools/) and [kind](https://kind.sigs.k8s.io/docs/user/quick-start/)

## kubectl vs the cluster version

* `kubectl` → the client, the remote control on my laptop
* `kindest/node` image → the cluster itself, the TV
* They don't have to match exactly → kubectl must be within **±1 minor version** of the API server
* My setup → `kubectl` `v1.37.2` + cluster `v1.37.0` → same minor (1.37) → fine

```bash
kubectl version --client
kind version
```

## Creating a cluster from a config file

* `kind-cluster.yaml` → 1 control-plane + 2 workers, pinned image

```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
    image: kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5
  - role: worker
    image: kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5
  - role: worker
    image: kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5
```

```bash
kind create cluster --name my-first-cluster --config kind-cluster.yaml
kind get clusters
docker ps                  # 3 containers = 3 nodes
kubectl get nodes -o wide
```

* Image tag + digest → copy both from the **kind release notes** for my kind version → GitHub `kubernetes-sigs/kind` releases → "Images pre-built for this release"
* kind v0.33.0 ships `v1.37.0` → that image needs kind v0.33.0 or newer
* Only the control-plane container publishes a port → `127.0.0.1:40627->6443/tcp` → 6443 = API server → that is how kubectl reaches the cluster

### Config file vs plain command

* `kind create cluster --name my-second-cluster` → no file → one node, kind's default image (change it with `--image`)
* Config file is better:
    * **version control** → in Git, easy to track and roll back
    * **declarative** → same cluster every time, on every machine
    * **shareable** → whole team gets the same setup
    * **single source of truth** → no "which flags did I use?"
* Same idea as Terraform, Ansible, Helm and Kubernetes manifests → YAML (or JSON) files describe the setup

## Lab: my first two clusters

1. Created `my-first-cluster` from the config file → 3 nodes
2. Created `my-second-cluster` with no file → 1 node
3. `kubectl get nodes` → showed only `my-second-cluster-control-plane` → kind switched my current context to the newest cluster
4. Second cluster showed `NotReady` at 20s old → normal, node turns Ready once the CNI (kindnet) is up, about 30–60s
5. Switched back with `kubectl config use-context kind-my-first-cluster`

| Symptom | Cause | Fix |
|---|---|---|
| Changed the tag to `v1.37.2` but kept the `v1.37.0` digest | Digest belongs to one exact image; with both given, Docker pulls by digest and ignores the tag | Use a tag + digest pair exactly as listed in the kind release notes |
| Wanted the node image to match my kubectl `v1.37.2` | kubectl is the client; only ±1 minor skew matters | Keep `v1.37.0` |
| `kubectl get clusters` → `the server doesn't have a resource type "clusters"` | A cluster doesn't know about other clusters; kubectl only lists objects inside one cluster | `kind get clusters` or `kubectl config get-contexts` |
| `kubectl get nodes` shows only the second cluster | `kind create cluster` sets the current context to the new cluster | `kubectl config use-context kind-my-first-cluster` |
| `kubectl config set-context kind-my-first-cluster` said "modified" but nothing changed | `set-context` **edits** a context, it doesn't switch | `use-context` switches |
| `kubectl get pods` → `No resources found in default namespace` | No Pods created yet; system Pods live in `kube-system` | `kubectl get pods -n kube-system` |

## The kubeconfig file

* File that tells kubectl **which clusters exist, how to reach them, and who I am on each**
* Default path → `~/.kube/config` | without it kubectl doesn't know where any cluster is
* Analogy → phone contacts + saved Wi-Fi passwords → clusters = addresses, users = logins, contexts = saved shortcuts, current-context = who I'm on a call with right now

### Its four sections

```yaml
apiVersion: v1
kind: Config
clusters:                              # WHERE
- name: kind-my-first-cluster
  cluster:
    server: https://127.0.0.1:40627    # API server address
    certificate-authority-data: ...    # to trust the server's certificate
users:                                 # WHO
- name: kind-my-first-cluster
  user:
    client-certificate-data: ...       # my identity
    client-key-data: ...               # my private key
contexts:                              # WHERE + WHO + NAMESPACE
- name: kind-my-first-cluster
  context:
    cluster: kind-my-first-cluster
    user: kind-my-first-cluster
    namespace: default                 # optional
current-context: kind-my-first-cluster # which one kubectl uses now
```

* kind gives the cluster, user and context the **same name** → confusing | in real setups they usually differ (e.g. context `prod-context` → cluster `cluster-3` + user `varun-user`)
* The certificate here is the **authentication** step ("who are you") → then RBAC decides what I'm allowed to do → see [RBAC & Request Flow](rbac.md)

### When the file changes

* Changes when I change **clusters or contexts**:
    * create a cluster → `kind create cluster`, `aws eks update-kubeconfig --name my-cluster`
    * delete a cluster → `kind delete cluster`
    * switch context → `kubectl config use-context`
    * edit a context → `kubectl config set-context`
* Does **not** change when I create, delete or scale Pods, Deployments, Services → those live inside the cluster, in etcd
* kubeconfig = address book for reaching clusters, not a record of what runs in them
* Check → `md5sum ~/.kube/config` before and after `kubectl create deployment` (same) vs `use-context` (different)

### Security

* Holds **credentials** → anyone with my kubeconfig has my access to the cluster (on prod, maybe full admin)
* Never commit it to Git, never paste it in chats or screenshots
* `chmod 600 ~/.kube/config` → only I can read it

## Contexts

* **Context** = cluster + user + namespace saved under one name
* Lets me switch between many clusters (dev, staging, prod) without retyping addresses and credentials
* Prevents running a command on the wrong cluster by accident → always check before anything destructive

```bash
kubectl config get-contexts               # list, * = current
kubectl config current-context            # just the current one
kubectl config use-context <name>         # SWITCH
kubectl get nodes --context <name>        # one command on another cluster, no switch
kubectl config view                       # whole file, secrets hidden
kubectl config view --minify              # only the current context
```

### set-context vs use-context

* `use-context` → **switches** to a context (changes the `current-context` line)
* `set-context` → **edits** a context's settings | with no settings given it changes nothing
* Real use of `set-context` → default namespace so I don't type `-n` every time

```bash
kubectl config set-context --current --namespace=kube-system
kubectl get pods                              # now kube-system Pods
kubectl config set-context --current --namespace=default
kubectl get pods --namespace=dev              # override for one command
```

## Namespaces (first look)

* Kubernetes **namespace** = a virtual cluster inside one real cluster → logical separation of resources
* Example → `dev`, `staging`, `prod` or one namespace per app on the same cluster
* Same name can exist in two namespaces (`web` in `dev` and `web` in `prod`) without conflict
* Built-in ones → `default`, `kube-system` (control-plane Pods), `kube-public`, `kube-node-lease`
* Not the same as Linux namespaces (process isolation) → different idea, same word

## Other ways kubectl finds a cluster

```bash
kubectl get nodes --kubeconfig /path/to/other-config
export KUBECONFIG=~/.kube/config:~/work-config     # merge several files
```

## Cleanup

```bash
kind delete cluster --name my-second-cluster
kind get clusters
```

!!! tip "Quick revision"

    * kind = Kubernetes in Docker, each node is a container
    * Pin node images with tag + digest from the kind release notes
    * kubeconfig = clusters + users + contexts + current-context
    * use-context switches, set-context edits

!!! question "Interview points"

    * What is kind? → a tool that runs Kubernetes clusters locally, with each node as a Docker container; used for learning, testing and CI
    * Why create a kind cluster from a config file? → version control, reproducible and declarative setup, shareable across the team, single source of truth
    * Must kubectl match the cluster version exactly? → no, kubectl is supported within one minor version of the API server
    * What is a kubeconfig? → kubectl's config file, ~/.kube/config by default, with clusters (API server + CA), users (credentials) and contexts that pair a cluster with a user and namespace; current-context decides where kubectl points
    * What is a context? → a saved combination of cluster, user and namespace
    * use-context vs set-context? → use-context switches the current context; set-context edits a context, e.g. its default namespace
    * Does the kubeconfig change when you create a Deployment? → no, only when clusters or contexts change; workloads live in etcd inside the cluster
    * Why is the kubeconfig sensitive? → it holds credentials; whoever has it has your access to the cluster
    * How do you avoid running a command on the wrong cluster? → check current-context before acting, use clear context names, or pass --context explicitly
    * Kubernetes namespace vs Linux namespace? → a Kubernetes namespace groups API objects logically; a Linux namespace isolates what a process can see
