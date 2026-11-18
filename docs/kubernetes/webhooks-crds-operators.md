# Webhooks, CRDs & Operators

## Webhooks in general

* Webhook = **"when something happens, call this URL"**
* A system sends an HTTP request (usually `POST` with JSON) to a URL I registered, as soon as an event happens
* **Polling** → I keep asking "anything new?" every few minutes | **webhook** → it tells me the moment it happens
* Analogy → food delivery app: without a webhook I keep opening the app to check | with one, I get a notification "out for delivery"
* API vs webhook → API = **I call them** when I want data (pull) | webhook = **they call me** when something happens (push)

### DevOps example: GitHub → Jenkins

1. Tell GitHub → "on every push, `POST` to `https://jenkins.example.com/github-webhook/`"
2. I push code
3. GitHub sends Jenkins a message → repo, branch, commit, author
4. Jenkins starts the build
* Without it → Jenkins would poll GitHub every minute → wasteful and slow
* Others → Stripe → my app ("payment succeeded") | Alertmanager → Slack/PagerDuty | GitHub → Argo CD

## Admission controllers

* Checks **inside the API server** that run after authentication and authorization, **before** anything is saved to etcd
* Inspect every create/update/delete request → **modify it** or **approve/reject it**
* Final safety and policy layer → makes Kubernetes customizable and policy-driven without changing its code
* Analogy → security guards at a building entrance

### The two kinds

* **Mutating** → the guard who fixes things → "you forgot your badge, I'll attach one" → **changes** the object
    * Examples → inject an Istio sidecar container, add default labels, set default values
* **Validating** → the guard who says yes or no → "carrying a weapon, not allowed in" → can only **allow or deny**
    * Examples → block Pods running as root or privileged, only allow images from our registry, require resource limits, enforce naming rules
* Order → **mutating first, then validating** → so validation checks the final version of the object

### Full request flow

1. API handler receives the request (raw YAML from kubectl or a controller)
2. Authentication + authorization (RBAC)
3. Mutating admission → built-in plugins and **mutating webhooks** change the object
4. Object schema validation → correct `apiVersion`, fields, types
5. Validating admission → built-in plugins and **validating webhooks** inspect the final object
6. Approved → saved to etcd | denied → error returned, object never created

### Admission webhooks

* Built-in admission plugins are compiled into the API server → **webhooks** let me add my own logic as an external HTTP service
* API server pauses the request → calls my webhook → "modify this?" or "allow this?" → continues based on the answer
* Registered with `MutatingWebhookConfiguration` and `ValidatingWebhookConfiguration` objects
* Tools built on this → **Kyverno**, **OPA Gatekeeper** (policy), **Istio** (sidecar injection), **cert-manager**

### The classic gotcha

* Webhook server is down + `failurePolicy: Fail` → the API server can't admit anything that matches → e.g. no new Pods can be created anywhere it applies
* Has broken real clusters, often during upgrades
* Guard against it → narrow the webhook's scope (`namespaceSelector`, exclude `kube-system`), short `timeoutSeconds`, run the webhook with several replicas
* Like a guard who must approve everyone, then goes missing → nobody enters

## CRDs (Custom Resource Definitions)

* Kubernetes ships with built-in types → Pod, Deployment, Service, ConfigMap
* A **CRD** teaches Kubernetes a **new object type** → `Database`, `Certificate`, `Backup`
* After that → `kubectl get databases` works exactly like `kubectl get pods` → stored in etcd, protected by RBAC, shown by kubectl
* Analogy → Kubernetes is a form office that accepts only certain forms → CRD = registering a new form type ("also accept the Database form, with fields name, version, size") → **Custom Resource (CR)** = one filled-in copy of that form

### Step 1: register the type (CRD)

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: databases.example.com        # <plural>.<group>
spec:
  group: example.com
  names:
    kind: Database
    plural: databases
  scope: Namespaced
  versions:
  - name: v1
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            properties:
              version: { type: string }
              size: { type: string }
```

### Step 2: create one (Custom Resource)

```yaml
apiVersion: example.com/v1
kind: Database
metadata:
  name: mydb
spec:
  version: "16"
  size: "10Gi"
```

```bash
kubectl get crds
kubectl apply -f crd.yaml
kubectl apply -f database.yaml
kubectl get databases
kubectl describe database mydb
```

### The catch

* **A CRD alone does nothing** → Kubernetes stores the `Database` object, but no database gets created
* A filled form sitting in a drawer → no Pods, no volumes, nothing happens
* To make it act → a **controller**

## Controllers and Operators

* **Controller** → a program that watches objects and reconciles real state towards them → same loop as the built-in Deployment and ReplicaSet controllers
* **CRD + custom controller = Operator** → automates what a human operator would do (create, back up, upgrade, fail over)
* Roles → CRD = the new form type | Custom Resource = a filled form | controller = the clerk who reads forms and does the work

| Operator / tool | Custom resource | What its controller does |
|---|---|---|
| cert-manager | `Certificate` | Gets and renews TLS certificates |
| Prometheus Operator | `ServiceMonitor` | Configures what Prometheus scrapes |
| Argo CD | `Application` | Syncs a Git repo into the cluster |
| CloudNativePG | `Cluster` | Runs and manages Postgres |
| Velero | `Backup`, `Restore` | Backs up and restores cluster resources |

* Written in Go with `client-go` / `controller-runtime` (Kubebuilder, Operator SDK)
* This is the extensibility that makes Kubernetes different from its competitors → see [Why Kubernetes](why-kubernetes.md)

!!! tip "Quick revision"

    * Webhook = "call this URL when X happens" (push, not poll)
    * Admission = mutating (change) then validating (allow/deny), after RBAC, before etcd
    * CRD = new object type | CR = one object of it | controller = acts on it | CRD + controller = operator

!!! question "Interview points"

    * What is a webhook? → an HTTP callback: a system pushes an event to a URL you registered instead of you polling it, like GitHub notifying Jenkins on a push
    * Webhook vs API? → with an API you pull data when you want it; with a webhook the other system pushes data when an event happens
    * What are admission controllers? → checks inside the API server, after authentication and authorization and before saving to etcd, that can modify or reject objects
    * Mutating vs validating admission? → mutating can change the object (e.g. inject a sidecar); validating can only allow or deny; mutating runs first
    * Why does order matter? → validation must check the final object, after all mutations
    * What happens if an admission webhook is down? → with failurePolicy Fail, matching requests are rejected, which can block Pod creation; scope webhooks narrowly and run them highly available
    * What is a CRD? → a way to extend the Kubernetes API with a new resource type, managed with kubectl like built-in objects
    * Does creating a custom resource do anything by itself? → no, it is only stored; a controller must watch and act on it
    * What is an operator? → a CRD plus a custom controller that automates running a piece of software, like cert-manager, Argo CD or Prometheus Operator
    * Tools built on admission webhooks? → Kyverno, OPA Gatekeeper, Istio, cert-manager
