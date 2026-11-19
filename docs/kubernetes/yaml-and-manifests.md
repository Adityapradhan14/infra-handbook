# YAML, Manifests & Objects

## Imperative vs declarative

* **Imperative** → tell the system *how*, step by step → `kubectl run web --image=nginx`
* **Declarative** → describe *what* the end result should be, the system works out the steps → write `pod.yaml` → `kubectl apply -f pod.yaml`
* Analogy → imperative = "copy file A to B, then run C" | declarative = "file A must exist at B with these permissions"
* Kubernetes is built around declarative → I describe desired state, controllers keep reconciling towards it

| | Imperative | Declarative |
|---|---|---|
| Example | `kubectl run`, `create`, `scale`, `set image` | `kubectl apply -f file.yaml` |
| Focus | The commands | The final state |
| Run it twice | `create` fails with "already exists" | Same result every time (**idempotent**) |
| Version control | Nothing to commit | YAML lives in Git → history, review, rollback |
| Good for | Quick tests, one-off fixes, exams | Everything that must last |

* In real jobs → **the YAML in Git is the source of truth** → changes go through the file, not ad-hoc commands
* Imperative commands are still useful → to *generate* YAML quickly (see [Generate YAML instead of writing it](#generate-yaml-instead-of-writing-it))

## YAML basics

* **YAML** = YAML Ain't Markup Language → human-readable data serialization format
* Data serialization → turning data structures (maps, lists, nested combinations) into text that humans can read and machines can parse
* Used everywhere in DevOps → Kubernetes, Helm, Ansible, Docker Compose, GitHub Actions, Prometheus
* Rules:
    * **Indentation = structure** → spaces only, **never tabs** → 2 spaces is the convention
    * `key: value` → the colon + space separates them
    * `#` → comment
    * Keys → lowercase, no spaces → `first_name`, `my-app`
* Extensions → `.yaml` or `.yml`

### The three building blocks

**1. Scalars** → single values

```yaml
first_name: Prakash     # string (quotes optional)
height: 5.9             # float
roll_number: 9          # integer
is_engineer: true       # boolean
pending_dues: null      # null
```

**2. Dictionaries (maps)** → key-value pairs, can nest

```yaml
address:
  street: that_street
  contact:              # nested dictionary
    phone: "000111222"
    email: prakash@example.com
```

**3. Lists** → items starting with `-`

```yaml
hobbies:
  - singing
  - traveling
args: ["sleep", "3600"]   # same thing, inline (flow) style
```

### Lists of dictionaries → the shape Kubernetes uses most

```yaml
work_experience:
  - company: ABC Corp     # item 1 = a dictionary with 2 keys
    role: DevOps Engineer
  - company: XYZ Inc      # item 2
    role: DevOps Consultant
```

* `-` starts a new item → keys under it at the same indent belong to that item
* `spec.containers` is exactly this → a list where each item is one container's dictionary

### YAML gotchas

* Tab instead of spaces → parse error
* Wrong indentation → a key silently lands under the wrong parent
* Values that look like other types → quote them when a string is expected:
    * `1.20` → float `1.2` | `"1.20"` → string
    * `yes`, `no`, `on`, `off` → may become booleans
    * Annotation and env values **must be strings** → `alb.ingress.kubernetes.io/healthcheck-interval-seconds: '15'`
* Validate → `yamllint`, the VS Code YAML extension, or `kubectl apply --dry-run=server`

| | YAML | JSON | XML |
|---|---|---|---|
| Structure | Indentation | `{}` and `[]` | `<tag></tag>` |
| Comments | Yes (`#`) | No | Yes (`<!-- -->`) |
| Readability | Best | OK | Verbose |
| Typical use | Config files | APIs | Legacy systems |

* JSON is valid YAML → Kubernetes accepts both → `kubectl get pod x -o json` / `-o yaml`

## What a Kubernetes object is

* An **object** = a record of something I want to exist in the cluster → a Pod, a Deployment, a Service
* The YAML file on my laptop is **not** the object → it is the description
* `kubectl apply` → API server validates it → saves it in **etcd** → now the object exists
* Analogy → an AC remote: setting 24°C = the object (desired) | room at 30°C = actual | AC keeps cooling until they match
* Every object has two halves:
    * **spec** → what I want → I write it
    * **status** → what is actually happening → Kubernetes writes it, I never do
* Controllers keep comparing spec vs status and fixing the difference → **reconciliation** (see [Why Kubernetes](why-kubernetes.md))

```bash
kubectl get pod web -o yaml     # my spec + a big status section I never wrote
```

## Anatomy of a manifest

* Every manifest has the same four top-level fields:

```yaml
apiVersion: v1        # which API group + version
kind: Pod             # which type of object
metadata:             # identity → name, namespace, labels, annotations
  name: web
spec:                 # desired state → different for every kind
  containers: ...
```

* Other names for manifests → config files, spec files, definition files, Kubernetes YAML → all the same thing

### apiVersion

* Format → **`group/version`**
* **API groups** → related object types bundled together | analogy → departments in a government office
* **Core group** → the original basic objects → has no name → written as just `v1`
* Every other group → `group/version`

| Object | apiVersion | Group |
|---|---|---|
| Pod, Service, Namespace, ConfigMap, Secret, PVC | `v1` | core |
| Deployment, ReplicaSet, StatefulSet, DaemonSet | `apps/v1` | apps |
| Job, CronJob | `batch/v1` | batch |
| Ingress | `networking.k8s.io/v1` | networking.k8s.io |
| StorageClass | `storage.k8s.io/v1` | storage.k8s.io |
| ReplicationController (legacy) | `v1` | core |

* **Version stages** → `v1alpha1` (experimental, may vanish) → `v1beta1` (mostly stable) → `v1` (stable)
* Old versions get **removed** → e.g. Ingress went `extensions/v1beta1` → `networking.k8s.io/v1beta1` → `networking.k8s.io/v1` → old tutorials break on new clusters
* What `apiVersion` + `kind` do → tell the API server **which schema** to validate the YAML against → unknown field = rejected
* Wrong pair → `apiVersion: v1` + `kind: Deployment` → error, Deployment is not in the core group

### apiVersion is not where objects are stored

* `apiVersion` is only a label on the form → it doesn't store anything
* The **API server** checks the object and saves it in **etcd** under a path-like key:

```
/registry/pods/default/web
          │      │      │
        type  namespace name
```

* Where `apiVersion` *does* show up → the API server's URL paths:
    * core group → `/api/v1/namespaces/default/pods/web`
    * named group → `/apis/apps/v1/namespaces/default/deployments/web`

```bash
kubectl get pod web -v=6                            # shows the GET .../api/v1/... request kubectl sends
kubectl get --raw /api/v1/namespaces/default/pods/web   # call the URL directly → JSON
```

### Looking things up instead of memorizing

```bash
kubectl api-resources                  # every type: NAME, SHORTNAMES, APIVERSION, NAMESPACED, KIND
kubectl api-versions                   # every group/version the cluster serves
kubectl explain deployment             # GROUP + VERSION + description
kubectl explain pod.spec.containers    # what a field means, drill down with dots
kubectl explain pod --recursive | less # the whole field tree
```

| Kind | Short name | apiVersion |
|---|---|---|
| Pod | `po` | `v1` |
| Service | `svc` | `v1` |
| ReplicationController | `rc` | `v1` |
| ReplicaSet | `rs` | `apps/v1` |
| Deployment | `deploy` | `apps/v1` |
| Namespace | `ns` | `v1` |

## Example: a multi-container Pod

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-pod-2
  labels:                        # nested dictionary
    app: nginx
    environment: development
spec:
  containers:                    # list of dictionaries
    - name: nginx-container
      image: nginx               # no tag = nginx:latest → pin a version in real setups
      ports:
        - containerPort: 80      # documentation only, does not open or publish anything
    - name: sidecar-container
      image: busybox
      args: ["sleep", "3600"]    # keep busybox alive for 1 hour
```

* **One Pod, two containers** → both share the Pod's network → same IP, reach each other on `localhost`
* `containerPort` → informational → nginx listens on 80 either way → exposing it needs a Service
* `busybox` has no long-running process → without `sleep` it exits instantly → CrashLoopBackOff
* After 3600s `sleep` ends → container exits → `restartPolicy: Always` (default) restarts it → restart count goes up
* Files are **not** shared → only through a declared volume (none here)
* "sidecar" here is just a name → **native sidecars** (1.29+) are declared under `initContainers` with `restartPolicy: Always` → guaranteed to start before the main container

```bash
kubectl apply -f pod.yaml
kubectl get pods                                     # READY 2/2
kubectl exec -it my-pod-2 -c sidecar-container -- sh
wget -qO- localhost                                  # nginx page, from the busybox container
kubectl logs my-pod-2 -c nginx-container             # -c required with >1 container
```

## Generate YAML instead of writing it

* Nobody writes manifests from memory → let kubectl write the skeleton

```bash
kubectl run web --image=nginx --dry-run=client -o yaml > pod.yaml
kubectl create deployment web --image=nginx --replicas=3 --dry-run=client -o yaml > deploy.yaml
```

* `--dry-run=client` → build the object locally, send nothing
* `--dry-run=server` → send it to the API server for full validation, but don't save → catches typos before applying

### Reading validation errors

```
strict decoding error: unknown field "spec.template.metadata.label"
```

* **unknown field** → a field name that isn't in the schema → almost always a typo
* The path tells me where → here `label` should be `labels`
* Other common ones → `selector does not match template labels` | `Required value` (missing field)

## kubectl apply and last-applied-configuration

* `kubectl apply` stores a copy of my file in the object → annotation `kubectl.kubernetes.io/last-applied-configuration`
* Next apply → compares 3 things → **my file now** vs **last-applied copy** vs **live object** → works out what to change (three-way merge)
* Imperative changes (`set image`, `scale`, `rollout undo`, `edit`) change the live object but **not** that copy → file, copy and cluster drift apart
* That is the warning on `kubectl rollout undo` → "previously managed with kubectl apply…"
* Fix → update the YAML to match what I want → `kubectl apply -f` again
* `create` vs `apply` → `create` only creates (fails if it exists) | `apply` creates or updates

## kubectl command shape

* Most commands → `kubectl <verb> <type> <name>`
* `rollout`, `set`, `scale` need the type → `kubectl rollout status deploy/web` or `deploy web`
* Without it → `the server doesn't have a resource type "web"` → kubectl read the name as a type
* Use the exact name → `kubectl get <type>` first and copy it → `NotFound` = wrong name or wrong namespace
* Plural when listing, singular when acting on one → `config get-contexts` vs `config use-context`
* Tab completion saves most typos:

```bash
echo 'source <(kubectl completion bash)' >> ~/.bashrc
echo 'alias k=kubectl' >> ~/.bashrc
echo 'complete -o default -F __start_kubectl k' >> ~/.bashrc
source ~/.bashrc
```

## Pod commands

```bash
kubectl apply -f pod.yaml
kubectl get pods
kubectl get pods -o wide                         # IP + node
kubectl get pods --show-labels
kubectl describe pod <pod>                       # Events at the bottom = why it's failing
kubectl logs <pod>
kubectl logs <pod> -c <container>                # one container of a multi-container Pod
kubectl logs -f <pod>                            # follow
kubectl logs <pod> --previous                    # logs from the crashed attempt
kubectl exec -it <pod> -- sh
kubectl exec -it <pod> -c <container> -- sh
kubectl get events --sort-by=.metadata.creationTimestamp
kubectl delete pod <pod>
```

!!! tip "Quick revision"

    * Imperative = commands (how) | declarative = YAML + `apply` (what) → declarative is idempotent and lives in Git
    * YAML = scalars, dictionaries, lists → spaces not tabs → quote strings that look like numbers or booleans
    * Object = desired state saved in etcd → spec (mine) vs status (Kubernetes')
    * Manifest = `apiVersion`, `kind`, `metadata`, `spec`
    * `apiVersion` = `group/version` → core group is just `v1`, Deployment is `apps/v1`
    * Don't memorize → `api-resources`, `explain`, `--dry-run=client -o yaml`

!!! question "Interview points"

    * Imperative vs declarative in Kubernetes? → imperative runs commands that act directly (`kubectl run`, `scale`); declarative describes desired state in a manifest and `kubectl apply` reconciles towards it, idempotently and version-controlled
    * What is a Kubernetes object? → a persisted record of desired state, stored in etcd via the API server, with a spec written by the user and a status written by Kubernetes
    * spec vs status? → spec is the desired state, status is the observed state; controllers work to make status match spec
    * What are the required top-level fields of a manifest? → apiVersion, kind, metadata, and spec (for most kinds)
    * Why is a Pod `v1` but a Deployment `apps/v1`? → Pods are in the unnamed core API group, Deployments are in the apps group; apiVersion is group/version
    * What do alpha, beta and v1 mean? → stability levels; alpha is experimental, beta is mostly stable, v1 is stable; old versions are removed in later releases
    * Where are objects stored? → in etcd, written only by the API server, under keys like /registry/pods/namespace/name
    * How do you find the apiVersion or fields of a resource? → `kubectl api-resources` and `kubectl explain <kind>.<field>`
    * How do you validate a manifest without creating it? → `kubectl apply --dry-run=server -f file.yaml`
    * What is last-applied-configuration? → an annotation where kubectl apply stores the last applied manifest, used for a three-way merge on the next apply; imperative changes don't update it
    * Do two containers in one Pod share a filesystem? → no, they share the network namespace; files are shared only through volumes
    * Does containerPort expose a port? → no, it is informational; a Service exposes Pods
