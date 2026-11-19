# Kubernetes

Notes on Kubernetes, written while working through the CKA course on a local `kind` cluster. They start with why Kubernetes exists and how a cluster is built, then the YAML and objects everything is written in, then go one layer deeper each chapter: what really happens on `kubectl apply`, how a Pod becomes a Linux process, how etcd stays consistent, and how access control and extensions work.

<div class="ih-chapters" markdown>

1. [Why Kubernetes](why-kubernetes.md)
    Docker's limits, desired state and reconciliation, Kubernetes vs Swarm, Compose, ECS
2. [Architecture](architecture.md)
    Control plane, worker nodes, API server, scheduler, controllers, kubelet, CRI/CNI/CSI
3. [YAML, Manifests & Objects](yaml-and-manifests.md)
    Imperative vs declarative, YAML types, spec vs status, `apiVersion` and API groups
4. [Pods, ReplicaSets & Deployments](pods-replicasets-deployments.md)
    Nodes vs Pods, selectors, RC vs RS, rolling updates, change-cause, rollbacks
5. [kind, kubeconfig & Contexts](kind-and-kubeconfig.md)
    Local clusters, pinned node images, `~/.kube/config`, `use-context` vs `set-context`
6. [From kubectl apply to Running Pod](deployment-workflow.md)
    Each component's step, watching events, Pending vs CrashLoopBackOff
7. [Container Runtime Internals](container-runtime.md)
    Namespaces, cgroups, requests vs limits, `containerd`, `runc`, dockershim
8. [etcd & Raft](etcd-and-raft.md)
    Key-value store, WAL, Secrets are base64, leader election, quorum
9. [REST, gRPC & Protobuf](rest-grpc-protobuf.md)
    How components talk, `.proto` files, where Kubernetes uses each
10. [RBAC & Request Flow](rbac.md)
    Authentication, authorization, Roles and bindings, `kubectl auth can-i`
11. [Webhooks, CRDs & Operators](webhooks-crds-operators.md)
    Mutating vs validating admission, custom resources, controllers

</div>
