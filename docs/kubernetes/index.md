# Kubernetes

Notes on Kubernetes, written while working through the CKA course on a local `kind` cluster. They start with why Kubernetes exists and how a cluster is built, then the YAML and objects everything is written in, how a real app is split into tiers and microservices, and how Services connect them (and how to debug them when they don't), the imperative commands used to generate manifests and test from inside the cluster, and how namespaces split one cluster, then go one layer deeper each chapter: what really happens on `kubectl apply`, how a Pod becomes a Linux process, how etcd stays consistent, and how access control and extensions work.

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
6. [Three-Tier & Microservices](three-tier-and-microservices.md)
    Monolith vs three-tier vs microservices, middleware, where databases run, StatefulSets
7. [Services](services.md)
    ClusterIP, NodePort, LoadBalancer, ExternalName, `port` vs `targetPort` vs `nodePort`, DNS and iptables step by step
8. [Debugging Services & DNS](debugging-services.md)
    Debugging method, checklist, CoreDNS not Ready, kube-proxy CrashLoopBackOff, wrong `targetPort`
9. [Imperative Commands](imperative-commands.md)
    `--dry-run`, generating Deployments and Services, `containerPort`, fixed `nodePort`, labels, test Pods, Pod DNS
10. [Namespaces](namespaces.md)
    Built-ins, namespaced vs cluster-scoped, `-n`/`-A`, cross-namespace DNS, not isolation, default namespace, quotas
11. [From kubectl apply to Running Pod](deployment-workflow.md)
    Each component's step, watching events, Pending vs CrashLoopBackOff
12. [Container Runtime Internals](container-runtime.md)
    Namespaces, cgroups, requests vs limits, `containerd`, `runc`, dockershim
13. [etcd & Raft](etcd-and-raft.md)
    Key-value store, WAL, Secrets are base64, leader election, quorum
14. [REST, gRPC & Protobuf](rest-grpc-protobuf.md)
    How components talk, `.proto` files, where Kubernetes uses each
15. [RBAC & Request Flow](rbac.md)
    Authentication, authorization, Roles and bindings, `kubectl auth can-i`
16. [Webhooks, CRDs & Operators](webhooks-crds-operators.md)
    Mutating vs validating admission, custom resources, controllers

</div>
