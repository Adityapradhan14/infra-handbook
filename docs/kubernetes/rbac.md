# RBAC & Request Flow

## Every request passes three gates

* Every request to the API server (from me, a controller or an app) goes through, in order:
    1. **Authentication** → who are you? (client certificate from kubeconfig, token, OIDC)
    2. **Authorization** → are you allowed to do this? → **RBAC lives here**
    3. **Admission control** → should this exact object be accepted, or changed first? → see [Webhooks, CRDs & Operators](webhooks-crds-operators.md)
* Fails any gate → request rejected, nothing is stored

## What RBAC is

* **Role-Based Access Control** → decides **who** can do **what** on **which** resources, **where**
* Permissions are given to roles, then roles are given to people or apps
* Without it → every user would be admin → one wrong command could delete production

### Office analogy

* I join a company and get an ID card
* **Me** → the subject
* **Job description** → "can enter the server room and read logs, can't delete anything" → the **Role**
* **HR assigning that job to me** → "Aditya gets server-room-reader, on Floor 2 only" → the **RoleBinding**
* **Floor 2** → a namespace | **whole building** → the cluster
* When I swipe at a door → system checks: does Aditya have a job that allows this, on this floor? → door opens or stays shut
* A job description nobody holds does nothing → a Role alone gives no one access until a binding connects it to someone

## The four objects

| Object | What it does | Scope |
|---|---|---|
| Role | A set of permissions | One namespace |
| ClusterRole | A set of permissions | Whole cluster (or reusable in many namespaces) |
| RoleBinding | Gives a Role or ClusterRole to a subject | One namespace |
| ClusterRoleBinding | Gives a ClusterRole to a subject | Whole cluster |

## The four questions RBAC answers

1. **Who** → subject:
    * **User** → a human | Kubernetes has no User object, users come from certificates or OIDC
    * **Group** → a set of users
    * **ServiceAccount** → identity for Pods and apps (CI/CD, operators) | a real Kubernetes object
2. **Can do what** → verbs → `get`, `list`, `watch`, `create`, `update`, `patch`, `delete`
3. **On what** → resources → `pods`, `deployments`, `secrets`, `pods/log`
4. **Where** → namespace (Role/RoleBinding) or whole cluster (ClusterRole/ClusterRoleBinding)

## Example: read-only Pods in `dev`

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: dev
rules:
- apiGroups: [""]                 # "" = core group (pods, services, configmaps)
  resources: ["pods", "pods/log"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: dev
subjects:
- kind: ServiceAccount
  name: monitor
  namespace: dev
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

## Rules that matter

* **Additive only** → no "deny" rules → anything not explicitly allowed is denied
* **Least privilege** → give only the verbs and resources actually needed → avoid `cluster-admin` and `*` wildcards
* **ClusterRole + RoleBinding** → define permissions once cluster-wide, grant them inside one namespace only → common trick
* `roleRef` **can't be changed** after creation → delete and recreate the binding
* Built-in ClusterRoles worth knowing → `view`, `edit`, `admin`, `cluster-admin`

## Commands

```bash
kubectl create namespace dev
kubectl create serviceaccount monitor -n dev

kubectl auth can-i list pods -n dev --as=system:serviceaccount:dev:monitor     # no

kubectl create role pod-reader --verb=get,list --resource=pods -n dev
kubectl create rolebinding read-pods --role=pod-reader --serviceaccount=dev:monitor -n dev

kubectl auth can-i list pods -n dev --as=system:serviceaccount:dev:monitor     # yes
kubectl auth can-i delete pods -n dev --as=system:serviceaccount:dev:monitor   # no

kubectl get roles,rolebindings -n dev
kubectl describe clusterrole view
kubectl auth can-i --list -n dev --as=system:serviceaccount:dev:monitor
```

* Break it → remove `list` from the Role → rerun `can-i` → try `kubectl get pods` as that ServiceAccount → read the `Forbidden` error, it names the verb, resource and namespace

## Where I'll use it

* Any in-cluster tool runs as a ServiceAccount → I write its ClusterRole myself
* Good interview story → "my tool needed read access to nodes, Pods and its CRDs, plus create only in its own namespace; here's how I scoped it"

!!! tip "Quick revision"

    * Request flow = authentication → authorization (RBAC) → admission → etcd
    * Role/ClusterRole = what is allowed | RoleBinding/ClusterRoleBinding = who gets it
    * Additive only, no deny → least privilege
    * Test with `kubectl auth can-i`

!!! question "Interview points"

    * What is RBAC in Kubernetes? → the authorization layer; Roles and ClusterRoles define allowed verbs on resources, RoleBindings and ClusterRoleBindings attach them to users, groups or ServiceAccounts
    * Role vs ClusterRole? → a Role is limited to one namespace; a ClusterRole is cluster-wide or reusable across namespaces
    * Can a RoleBinding reference a ClusterRole? → yes, and it grants those permissions only inside the binding's namespace
    * Can you write a deny rule? → no, RBAC is additive; anything not allowed is denied
    * Authentication vs authorization? → authentication proves who you are; authorization (RBAC) decides what you may do
    * Where do users come from? → outside Kubernetes, through certificates or OIDC; ServiceAccounts are the only identities stored as objects
    * How do you check permissions? → kubectl auth can-i, with --as to test another user or ServiceAccount
    * Can you change a binding's roleRef? → no, delete and recreate the binding
    * What is least privilege? → give each identity only the exact verbs and resources it needs, avoiding cluster-admin and wildcards
