# Three-Tier Architecture & Microservices

## Why this comes before Services

* Kubernetes Services only make sense once I know **what talks to what** in a real app
* A real app = frontend + backend + database (+ middleware in between) → each piece runs as its own Deployment → they find each other through Services
* This chapter = the app design | next chapter = the networking that connects it

## Monolithic architecture

* **Monolith** → UI, business logic and database access all in **one codebase**, deployed as **one unit**
* Simple to start → one repo, one build, one deploy
* Gets painful as it grows:

| Problem | What it means |
|---|---|
| Tightly coupled | Change in one part (e.g. payments) can break another (e.g. login) |
| Hard to maintain and upgrade | Any fix → rebuild, retest and redeploy the whole app → downtime, big test cycles |
| Limited scaling | Only the search feature is busy? Still have to scale the **entire** app → wasted CPU/RAM |
| Slow development | Many teams in one codebase → wait on each other, merge conflicts, risky releases |

* Still found in **legacy systems** that were never split up

## Three-tier architecture

* Splits the app into **separate logical layers** → each layer has one job → separation of concerns

```
User ─▶ Frontend (web tier) ─▶ Middleware ─▶ Backend (application tier) ─▶ Database (data tier)
```

| Tier | Job | Examples |
|---|---|---|
| **Frontend** (web tier) | What the user sees and clicks | HTML, CSS, JavaScript, React, Angular, Vue |
| **Middleware** | Sits between frontend and backend → auth, logging, caching, routing, messaging | API Gateway, Nginx, Express.js, Kafka, RabbitMQ |
| **Backend** (application tier) | Business logic → processes requests, talks to the database | Python, Node.js, Java, Go, .NET |
| **Database** (data tier) | Stores and retrieves data | MySQL, PostgreSQL, MongoDB, Redis |

* Middleware is often counted as part of the backend → that's why it's still called **three**-tier

### Each tier in an e-commerce site

* **Frontend** → homepage, product listing, cart page | click "Add to Cart" → request goes to the backend
* **Middleware** →
    * **Auth** → checks who I am (OAuth, JWT, API keys)
    * **Logging / monitoring** → ELK, Prometheus, Grafana
    * **Caching** → Redis, Memcached → avoid hitting the DB for the same data again
    * **Service communication** → API gateway routes requests, message brokers (Kafka, RabbitMQ) pass events between services
    * **Rate limiting** → blocks too many requests from one client
    * **Payment gateway** → validates the card before the order reaches the backend
* **Backend** → order management (create order, update stock, send email), wishlist
* **Database** → users table, products table, order history

## How three-tier apps were deployed over time

| Era | Setup | Good | Bad |
|---|---|---|---|
| **Single server** | All 3 tiers on one physical machine | Simple, cheap | Scale only vertically (bigger machine) → one busy tier slows everything → server dies = everything dies |
| **Three servers** (pre-virtualization) | One physical server per tier | Better performance, fault isolation | Expensive → 3× hardware, power, maintenance |
| **Virtualization** | One physical host, each tier in its own VM (VMware, KVM) | Isolation without buying 3 machines, resize VMs | Still heavy (each VM = full OS), slow to scale, manual |
| **Cloud + Kubernetes** | Each tier containerized, run as Deployments; DB often a managed service | Fast scaling, self-healing, automation, efficient | More moving parts to learn |

* Not the full list → event-driven and serverless models exist too

## Problems with plain three-tier

* Each tier is **still a monolith inside** → the whole backend is one codebase
* **Scaling** → orders are busy but wishlist isn't → still scale the whole backend tier
* **Single point of failure** → backend tier crashes → whole app down
* **Tight coupling** → one big backend codebase → risky deploys
* **Slow delivery** → teams wait on each other inside one tier
* **One tech stack per tier** → whole backend locked to one language
* Fix → break each tier into small independent services → **microservices**

## Microservices

* App split into **small, independent services** → each does **one business function** → they talk over APIs (HTTP/gRPC) or messages

```
Monolith:        [ login + products + orders + payments + wishlist ]   ← one app

Microservices:   [user-svc]  [product-svc]  [order-svc]  [payment-svc]  [wishlist-svc]
                     each built, deployed, scaled and failed independently
```

* E-commerce example →
    * **User service** → login, profiles
    * **Product service** → catalogue, inventory
    * **Order service** → orders, payments
    * **Wishlist service** → saved items
* **Fault isolation** → wishlist service crashes → users can still browse and order, only the wishlist is unavailable until it recovers
    * In a monolith → a wishlist bug can take the whole app down

| Benefit | Meaning |
|---|---|
| Independent scaling | Scale only the busy service (orders on sale day) |
| Fault isolation | One service failing doesn't crash the rest |
| Faster deployment | Each team ships its own service on its own schedule |
| Technology freedom | Orders in Java, search in Go, ML in Python |
| Easier maintenance | Small codebases → easier to read, test, debug |

* Naming → called "Wishlist **Service**", not "Wishlist Microservice" → every microservice is a service anyway, shorter, industry convention
* Trade-off (not free) → many services = more network calls, more things to monitor, harder debugging across services → that's why Services, DNS, observability and tracing matter so much

## Microservices on Kubernetes

* Each microservice → its own **Deployment** (its Pods) + its own **Service** (stable name to reach it)
* Each tier can hold many microservices:

| Tier | Microservices | In Kubernetes |
|---|---|---|
| Frontend | Web UI, mobile backend | Deployments + Service exposed to users (usually through Ingress) |
| Middleware | API gateway, auth, logging, caching | Deployments + internal Services |
| Backend | Order, payment, wishlist services | Deployments + internal (ClusterIP) Services |
| Database | MySQL, PostgreSQL | Usually **outside** the cluster (managed service) |

### Request flow in an e-commerce app on Kubernetes

1. User opens `https://example.com`
2. Request hits the **Ingress controller** → routes it to the **frontend Service** → one frontend Pod
3. Frontend calls the **API gateway** (middleware)
4. API gateway forwards to the right backend service → e.g. **wishlist Service** → one wishlist Pod
5. Wishlist Pod reads from the **database** → sends data back
6. User sees the updated wishlist

### Scaling each service

* Each microservice = its own Deployment → scaled separately
* **HPA** (Horizontal Pod Autoscaler) → adds/removes Pods of one Deployment based on load (CPU, memory, custom metrics) → orders can go to 20 Pods while wishlist stays at 2

## Where the database lives

### Stateless vs stateful

* **Stateless** → keeps nothing between requests → any Pod can answer any request → kill it, start another, nothing lost → easy to scale (frontend, most backends)
* **Stateful** → remembers data between requests → losing a Pod can lose data → needs stable identity + persistent storage (databases, Kafka, ZooKeeper)

### Why databases are usually not run in Kubernetes in production

* **Stateful is hard** → needs stable network identity, persistent volumes, replication, failover, backups → Kubernetes doesn't do all of that out of the box
* **Performance** → managed DBs and tuned VMs give better storage I/O
* **HA and backups** → replication, automatic failover, point-in-time restore are built into managed services

### Where they run instead

* **Managed database** → AWS RDS, Google Cloud SQL, Azure Database → backups, patching, failover handled for me
* **Dedicated VMs** with HA setup → full control over tuning
* **Hybrid** (most common) → apps in Kubernetes, database outside → apps reach it by DNS name (an **ExternalName** Service can give it a short in-cluster name → see [Services](services.md))

### When a database does run in Kubernetes

* **StatefulSet** → like a Deployment but each Pod gets:
    * a **stable name** → `mysql-0`, `mysql-1` (not random suffixes)
    * its **own persistent volume** that follows it across restarts
    * **ordered** start, scale and shutdown (`mysql-0` first)
* Use cases → MySQL, PostgreSQL, Kafka, ZooKeeper
* Good fits →
    * dev and test environments
    * with a **database Operator** (MySQL Operator, CloudNativePG for PostgreSQL) → an Operator is a custom controller with the DBA's knowledge coded in → handles backups, failover, upgrades (see [Webhooks, CRDs & Operators](webhooks-crds-operators.md))
    * small self-managed setups

!!! tip "Quick revision"

    * Monolith → one codebase, one deploy → coupled, scale everything together
    * Three-tier → frontend, (middleware), backend, database → separated layers, but each tier is still a monolith inside
    * Microservices → small services per business function → scale, deploy and fail independently
    * In Kubernetes → one Deployment + one Service per microservice
    * Databases → usually managed services outside the cluster; StatefulSets or Operators when inside

!!! question "Interview points"

    * What are the three tiers? → presentation (frontend), application (backend, often with middleware), and data (database)
    * What does middleware do? → sits between frontend and backend for auth, logging, caching, rate limiting and routing, e.g. an API gateway or message broker
    * Monolith vs microservices? → a monolith is one codebase deployed as one unit; microservices split the app into small services deployed and scaled independently
    * Main benefit of microservices? → independent scaling and deployment, plus fault isolation so one failing service doesn't take down the app
    * Downside of microservices? → more network calls, more services to deploy and monitor, and harder debugging across service boundaries
    * How do microservices map to Kubernetes? → each service gets its own Deployment for its Pods and its own Service for a stable name
    * Stateless vs stateful? → stateless keeps no data between requests so any Pod can serve any request; stateful keeps data and needs stable identity and storage
    * Why are production databases often kept outside Kubernetes? → stateful workloads need persistent storage, replication, failover and backups, which managed services like RDS handle better
    * What is a StatefulSet? → a controller for stateful apps that gives each Pod a stable name, its own persistent volume and ordered startup
