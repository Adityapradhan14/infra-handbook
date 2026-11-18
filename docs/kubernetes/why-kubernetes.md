# Why Kubernetes

*Hands-on notes, CKA course Day 6 plus my own reading*

## The problem with Docker alone

* Docker → great at packaging and running containers **on one machine**
* Real apps → many containers, on many machines, running 24/7 → Docker alone can't manage that
* What Docker alone does not give you:

| Missing piece | What it means |
|---|---|
| Auto-scaling | Add or remove containers automatically when traffic goes up or down |
| Load balancing | Spread traffic across many copies of the same app, on many machines |
| Self-healing | Container crashes or a machine dies → something brings the app back on its own |
| Rolling updates / rollbacks | Ship a new version with zero downtime, undo it if it breaks |
| Scheduling | Decide which machine has free CPU and RAM for a new container |
| Service discovery | Containers keep changing IPs → others still need a stable name to reach them |

* Analogy → Docker is one chef cooking one dish well | Kubernetes is the restaurant manager running 50 chefs in 5 kitchens, replacing anyone who calls in sick

## What Kubernetes is

* Kubernetes (K8s) → a **container orchestrator** → runs and manages containers across a group of machines called a **cluster**
* K8s → 8 letters between K and s | Greek for "helmsman" (the person who steers a ship) | open-sourced by Google in 2014, now a CNCF project
* It does not replace Docker images → it runs the same OCI images, just at scale
* You describe **what** you want, Kubernetes works out **how**

## Desired state and reconciliation

* The core idea of Kubernetes → everything else is built on it
* You never say "start a container on node 2" → you declare the **desired state**: "I want 3 copies of this image, 512Mi memory each, reachable on port 80"
* That declaration is stored in the cluster's database (etcd)
* **Controllers** keep comparing desired state with **actual state** → any difference gets fixed automatically
* This loop is called **reconciliation** and it never stops

```
desired: 3 pods  →  actual: 2 pods  →  controller creates 1  →  actual: 3 pods  ✓
desired: 3 pods  →  actual: 4 pods  →  controller deletes 1  →  actual: 3 pods  ✓
```

* Analogy → AC thermostat: you set 24°C (desired), it keeps measuring the room (actual) and switches the cooling on or off until they match
* Declarative (say the end result) vs imperative (give step-by-step commands) → same idea as Terraform

## What Kubernetes gives you

* **Scheduling** → picks the right machine for each container based on free CPU/RAM and rules
* **Self-healing** → container crashes → restarted | machine dies → its containers are recreated on another machine
* **Scaling** → more or fewer copies of an app (HPA) | more or fewer machines (Cluster Autoscaler, Karpenter)
* **Service discovery + load balancing** → Services give a stable name and IP in front of changing containers
* **Rolling updates + rollbacks** → new version rolled out gradually, old version kept for instant undo
* **Config and secrets** → ConfigMaps and Secrets, kept separate from the image
* **Storage** → persistent volumes attached wherever the container lands
* **Extensibility** → you can add your own object types to the API (CRDs + operators) → see [Webhooks, CRDs & Operators](webhooks-crds-operators.md)

## Kubernetes vs Docker Swarm vs Docker Compose

| | Kubernetes | Docker Swarm | Docker Compose |
|---|---|---|---|
| What it is | Full orchestrator for a cluster | Docker's built-in simple orchestrator | Tool to define multi-container apps |
| Machines | Many (multi-host cluster) | Many (multi-host, smaller scale) | One host only |
| Complexity | High | Low | Lowest |
| Scaling | Automatic + manual | Manual, limited | Manual |
| Self-healing | Strong (restarts, reschedules) | Basic (restarts) | None |
| Load balancing | Built-in, advanced | Basic (routing mesh) | Not built in |
| Networking | Advanced (Services, Ingress/Gateway, network policies) | Overlay network | Docker's default networking |
| Stateful apps | StatefulSets, Persistent Volumes | Limited | Volumes only |
| Ecosystem | Huge (Helm, Argo CD, Prometheus, Istio) | Small, mostly stagnant | Large, but for local dev |
| Best for | Production at any scale, microservices | Small production setups | Local development and testing |

## Kubernetes vs the other options

| | Kubernetes | Nomad | ECS | Serverless (Lambda / Cloud Run) |
|---|---|---|---|---|
| Complexity | High | Medium | Low–Medium | Lowest |
| Portability | Any cloud or on-prem | Any | AWS only | Locked to the vendor |
| Extensibility | CRDs + operators extend the API itself | Plugins | None | None |
| Workloads | Containers (VMs via KubeVirt) | Containers, VMs, plain binaries | Containers | Functions / short-lived containers |
| Hiring market | Industry standard | Niche | Common in AWS shops | Common |

## Real advantages

* **Extensibility** → teach Kubernetes new object types (a Postgres cluster, a backup, a GPU job) and manage them exactly like built-in ones → no competitor has this
* **Portability** → the same YAML runs on EKS, GKE, AKS, bare metal or `kind` on my laptop
* **Ecosystem** → almost every infra tool supports Kubernetes first | AI infra (GPU scheduling, Kubeflow, KServe, Ray) is built on it

## Real downsides

* Operationally heavy → upgrades, CNI networking, RBAC, lots of YAML
* Overkill for small apps → 3 services are often better on ECS or Cloud Run
* Costs money when used badly → idle nodes, oversized resource requests
* Steep learning curve → debugging needs Linux, networking and control-plane knowledge
* Knowing when **not** to use Kubernetes is part of knowing Kubernetes

!!! tip "Quick revision"

    * Kubernetes = container orchestrator for a cluster of machines
    * Core idea = desired state stored in etcd + controllers reconciling actual state towards it
    * Docker runs containers, Kubernetes runs them at scale with scheduling, healing, scaling and rollouts

!!! question "Interview points"

    * What is Kubernetes? → a declarative container orchestrator; controllers keep reconciling actual state towards the desired state stored in etcd, handling scheduling, self-healing, scaling, service discovery and rollouts
    * Why not just Docker? → Docker runs containers on one machine; it has no built-in auto-scaling, multi-host load balancing, self-healing or rolling updates across a cluster
    * Declarative vs imperative? → declarative = you describe the end state and the system works out the steps; imperative = you give each step yourself
    * What is reconciliation? → the never-ending loop where a controller compares desired and actual state and fixes the difference
    * Kubernetes vs Docker Swarm? → Swarm is simpler and built into Docker but has a small ecosystem and basic features; Kubernetes is more complex but is the industry standard with auto-scaling, strong self-healing and a huge ecosystem
    * Kubernetes vs ECS? → ECS is simpler and AWS-only; Kubernetes is portable and extensible through CRDs and operators
    * Biggest advantage of Kubernetes over competitors? → its extensible API (CRDs + operators), plus portability and the ecosystem
    * When would you not use Kubernetes? → small teams with a few services, where ECS or Cloud Run gives the same result with far less operational work
