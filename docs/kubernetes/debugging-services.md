# Debugging Services & DNS

## The method

* Nobody knows every error in advance → debugging is a **method**, not memory → narrow the problem down one layer at a time
* Steps →
    1. **Exact symptom** → copy the exact error, not "it's not working"
    2. **Split the path in half** → every test should cut the problem in two (name fails but IP works → DNS)
    3. **Status first** → `get` → `describe` → `logs` (`logs --previous` if it crashes)
    4. **Compare working vs broken** → one Pod fine, one not? → what's different (node, config, version)
    5. **Go one layer down** → Pod → node → host → the cause can sit several layers below the symptom
    6. **Search the exact error line** in quotes → normal, everyone does it
    7. **Fix → verify → write down the cause**

## The path a Service request depends on

```
curl backend-svc:9090
  → DNS lookup                    (Pod's /etc/resolv.conf → kube-dns Service 10.96.0.10)
    → CoreDNS Pods Ready          (else kube-dns has no endpoints)
      → CoreDNS reaches the API server (kubernetes Service 10.96.0.1:443) to learn Service names
        → kube-proxy rules on the node (make ClusterIPs work at all)
          → kube-proxy running     (needs host kernel resources)
  → Service ClusterIP:port → iptables DNAT
    → Endpoints not empty         (selector matches, Pods Ready, same namespace)
      → targetPort = the app's real port
        → app listening and answering
```

* Any link breaks → the request fails → the error message tells which half to look at

## Checklist

```bash
# 1. Service exists, right namespace, right ports?
kubectl get svc -A | grep <name>
kubectl describe svc <name>                       # Selector, Port, TargetPort, Endpoints

# 2. Does it have endpoints?
kubectl get endpointslices -l kubernetes.io/service-name=<name>
kubectl get pods --show-labels -o wide            # labels match the selector? Pods Ready (1/1)?

# 3. Name vs IP (from a test Pod)
kubectl exec -it <pod> -- curl <svc>:<port>        # by name
kubectl exec -it <pod> -- curl <clusterIP>:<port>  # by IP → works = DNS problem
kubectl exec -it <pod> -- curl <podIP>:<targetPort>  # straight to a Pod → works = Service/port problem

# 4. DNS
kubectl exec -it <pod> -- cat /etc/resolv.conf     # nameserver 10.96.0.10
kubectl get svc -n kube-system                     # kube-dns 10.96.0.10
kubectl get pods -n kube-system -l k8s-app=kube-dns -o wide
kubectl logs -n kube-system -l k8s-app=kube-dns --tail=20
kubectl run test --rm -it --image=busybox -- nslookup <svc>

# 5. kube-proxy (Service rules on each node)
kubectl get pods -n kube-system -l k8s-app=kube-proxy -o wide
kubectl logs -n kube-system <kube-proxy-pod> --previous --tail=20
```

## Symptom → likely cause

| Symptom | Likely cause | Check |
|---|---|---|
| `Could not resolve host: <svc>` | DNS broken, typo in name, or Service in another namespace | `get svc -A`, CoreDNS Pods Ready, `curl <clusterIP>` |
| `Could not resolve host: backend` + `svc` | Space instead of `-` → curl saw two hosts | Fix the typo |
| Connection refused / browser "empty response" | `targetPort` ≠ app's real port, or app not listening | `describe svc` TargetPort vs app config |
| Request hangs / times out | No Ready endpoints, or kube-proxy rules stale | Endpoints, kube-proxy Pods |
| `Endpoints: <none>` | Selector ≠ Pod labels, Pods not Ready, wrong namespace | `get pods --show-labels`, readiness |
| Pod `0/1 Running` | Running but failing readiness probe → removed from Services | `describe pod`, logs |
| Pod `CrashLoopBackOff` | Starts, exits, restarts again and again | `logs --previous` |
| LoadBalancer `EXTERNAL-IP <pending>` | No cloud controller (kind, bare metal) | Normal locally → MetalLB / cloud-provider-kind |

## Incident: Service name doesn't resolve on kind (DNS → kube-proxy → inotify)

### Symptom

```
# curl backend-svc:9090
curl: (6) Could not resolve host: backend-svc
```

### Simple version

* Think of the cluster as an office building →
    * **CoreDNS** = phonebook operator → "what's backend-svc's number?"
    * **API server** = main office register → has every Service and its number
    * **kube-proxy** = switchboard operator on each floor → connects calls to the right place
    * **Nodes** = floors | **my laptop** = the land the building stands on
* What went wrong →
    1. Asked the phonebook for `backend-svc` → no reply
    2. Called `backend-svc` directly by its number → **worked** → so the reception (Service) was fine, the phonebook was the problem
    3. Both phonebook operators were marked **not ready**
    4. Their complaint → "I can't reach the main register" → no list → refuse to work
    5. After a restart one operator (on floor worker2) was fine, the one on floor worker still stuck → problem is **on that floor**
    6. Switchboard operators (kube-proxy) → floor worker2 fine, floors worker and control-plane **kept fainting** (crashing 180+ times)
    7. Why → "too many open files" → the **land** (my laptop) ran out of a resource the operators need
    8. Fix → raise that limit on the laptop → replace the fainted operators → replace the stuck phonebook operator
* One sentence → **host ran out of inotify instances → kube-proxy kept crashing → CoreDNS couldn't reach the API server → DNS stopped → Pods couldn't find Services by name**

### Investigation, step by step

**1. Does the Service exist?**

```
$ kubectl get svc
NAME          TYPE        CLUSTER-IP      PORT(S)
backend-svc   ClusterIP   10.96.253.171   9090/TCP
```

* Exists, same namespace (`default`) as the test Pod → Service object is fine

**2. Name vs IP**

```
$ kubectl exec -it mynginx -- curl 10.96.253.171:9090
Hello from backend :)
```

* IP works, name fails → **DNS is the problem**, the Service data path is fine
* (Worked because that node still had the iptables rule from before kube-proxy started failing → stale but present)

**3. DNS components**

```
$ kubectl get pods -n kube-system -l k8s-app=kube-dns
NAME                       READY   STATUS    RESTARTS
coredns-559f6c778d-8cpvc   0/1     Running   3 (136m ago)
coredns-559f6c778d-kfxfx   0/1     Running   3 (136m ago)

$ kubectl exec -it mynginx -- cat /etc/resolv.conf
search default.svc.cluster.local svc.cluster.local cluster.local
nameserver 10.96.0.10
options ndots:5

$ kubectl get svc -n kube-system
NAME       TYPE        CLUSTER-IP   PORT(S)
kube-dns   ClusterIP   10.96.0.10   53/UDP,53/TCP,9153/TCP
```

* `resolv.conf` points to the right place, `kube-dns` Service exists
* But CoreDNS is **`0/1`** → **Running but not Ready**
* DNS is itself a Service → `kube-dns` (`10.96.0.10`) in front of the CoreDNS Pods → Services only route to **Ready** Pods → **0 endpoints** → nobody answers DNS queries
* `RESTARTS 3 (136m ago)` → laptop slept / Docker restarted about 2 hours earlier → common trigger with kind

**4. Why isn't CoreDNS Ready?**

```
$ kubectl logs -n kube-system -l k8s-app=kube-dns --tail=20
[INFO] plugin/ready: Plugins not ready: "kubernetes"
```

* CoreDNS doesn't store records itself → its **`kubernetes` plugin** watches the API server for Services and Pods to build its answers
* Plugin not ready = initial sync with the API server never finished → CoreDNS fails its readiness probe
* CoreDNS reaches the API server through the **`kubernetes` Service** → `10.96.0.1:443` → a ClusterIP → needs kube-proxy's rules on CoreDNS's node

**5. Restart CoreDNS and compare**

```
$ kubectl rollout restart deployment coredns -n kube-system
$ kubectl get pods -n kube-system -l k8s-app=kube-dns -o wide
NAME                       READY   NODE
coredns-66bc77855f-gpbdc   1/1     my-first-cluster-worker2
coredns-66bc77855f-wbd72   0/1     my-first-cluster-worker
```

* `rollout restart` → old Pods `Terminating` → `Completed`, new Pods `ContainerCreating` → `Running`
* Same image, same config → one Ready, one not → **the difference is the node**
* One Ready CoreDNS Pod is enough for DNS to work again → but the cluster isn't healthy yet

**6. kube-proxy on each node**

```
$ kubectl get pods -n kube-system -l k8s-app=kube-proxy -o wide
NAME               READY   STATUS             RESTARTS          NODE
kube-proxy-nb9dn   1/1     Running            210 (142m ago)    my-first-cluster-worker2
kube-proxy-qb7jn   0/1     CrashLoopBackOff   183 (83s ago)     my-first-cluster-control-plane
kube-proxy-vngnk   0/1     CrashLoopBackOff   182 (2m37s ago)   my-first-cluster-worker
```

* **CrashLoopBackOff** → container starts, crashes, kubelet restarts it, waits longer each time, repeats
* kube-proxy dead on `worker` → that node's Service rules never update → CoreDNS on `worker` can't reach `10.96.0.1` → stays `0/1`

**7. Why does kube-proxy crash?**

```
$ kubectl logs -n kube-system kube-proxy-vngnk --previous --tail=20
"command failed" err="failed complete: fsnotify watcher init: too many open files"
```

* `--previous` → logs of the **last crashed** container → where crash reasons live
* kube-proxy uses **inotify** (kernel feature: "tell me when this file changes") to watch its config
* Kernel limits inotify per user → `fs.inotify.max_user_instances` (default **128**) and `fs.inotify.max_user_watches`
* **kind nodes share the host's kernel** → 3 nodes × (kubelet, kube-proxy, other components) + VS Code + browser → limit exhausted → kube-proxy can't create its watcher → exits → crash loop

### Fix

```bash
# 1. Raise the limits now
sudo sysctl fs.inotify.max_user_watches=524288
sudo sysctl fs.inotify.max_user_instances=512

# 2. Persist across reboots
echo "fs.inotify.max_user_watches=524288" | sudo tee -a /etc/sysctl.conf
echo "fs.inotify.max_user_instances=512" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# 3. Replace the crashed kube-proxy Pods (DaemonSet recreates them immediately)
kubectl delete pod -n kube-system <kube-proxy-on-control-plane> <kube-proxy-on-worker>
kubectl get pods -n kube-system -l k8s-app=kube-proxy -o wide -w      # all 1/1, RESTARTS 0

# 4. Replace the stuck CoreDNS Pod (ReplicaSet recreates it)
kubectl delete pod -n kube-system <coredns-pod-that-is-0/1>
kubectl get pods -n kube-system -l k8s-app=kube-dns -o wide -w        # both 1/1

# 5. Verify
kubectl exec -it <test-pod> -- curl backend-svc:9090                 # Hello from backend :)
kubectl get endpointslices -n kube-system -l kubernetes.io/service-name=kube-dns
```

* Deleting a DaemonSet Pod is safe → DaemonSet = one Pod per node, always → recreated straight away
* New CoreDNS Pod may land on a different node → normal, the scheduler picks any node that fits
* Old restart counts on the healthy kube-proxy stay (e.g. 210) → history from before the fix → ignore if they don't grow

### Dependency chain (technical)

```
curl backend-svc:9090
  → needs DNS
    → CoreDNS Pods Ready
      → CoreDNS lists Services from the API server (10.96.0.1:443)
        → reaching a ClusterIP needs iptables rules
          → kube-proxy writes those rules
            → kube-proxy needs inotify watchers from the host kernel
              → host inotify limit too low   ← ROOT CAUSE
```

### What this incident teaches

* **Running ≠ Ready** → Services only send traffic to Ready Pods → a Running-but-not-Ready Pod is invisible to callers
* **Cluster DNS is just a Service + Pods** → `kube-dns` in front of CoreDNS → same rules as my own Services
* **DaemonSet** → one Pod per node, recreated on delete
* **CrashLoopBackOff → `logs --previous`**
* **kind shares the host kernel** → host limits (inotify, file descriptors) affect the whole cluster
* **Compare healthy vs broken** → same Pod on two nodes behaving differently = look at the node

## Incident: wrong targetPort → empty response

### Symptom

* Browser → `localhost:31000` → "localhost:31000 sent back an empty page" (`NS_ERROR_NET_EMPTY_RESPONSE`)
* Pods `1/1 Running`, Service created, Endpoints filled

### Cause

```yaml
spec:
  type: NodePort
  ports:
    - port: 9090
      targetPort: 5678     # ← copied from the backend Service
      nodePort: 31000
  selector:
    app: frontend          # but these Pods run nginx, which listens on 80
```

```
Browser → localhost:31000 → frontend-svc → nginx Pod:5678   ← nothing listening → connection cut
```

* Ports copied from the backend Service → selector now points at **nginx** Pods → nginx listens on **80**, not 5678

### Fix

```yaml
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
      nodePort: 31000
```

```bash
kubectl apply -f frontend.yaml
kubectl get svc frontend-svc       # 80:31000/TCP
curl localhost:31000               # Welcome to nginx!
```

### How to catch it

1. Pods Running + Endpoints filled + connection refused / empty response → suspect ports
2. `kubectl describe svc <name>` → read **TargetPort**
3. Does it match the app's real port? (nginx 80, http-echo 5678) → check the app's config if unsure
4. Mismatch → fix `targetPort`

## Building the skill

* Debugging only grows by facing broken things → break things on purpose, predict the error first, then debug it
* Break a kind cluster →
    * wrong `targetPort` | wrong selector label | Pod in another namespace
    * scale CoreDNS to 0 → `kubectl scale deploy coredns -n kube-system --replicas=0`
    * bad image name → `ImagePullBackOff`
    * stop a node container → `docker stop <node>`
* Practice →
    * [SadServers](https://sadservers.com/) → real broken Linux servers to fix in the browser → the base layer under everything
    * [Killercoda](https://killercoda.com/) → free Kubernetes scenarios, including CKA-style troubleshooting
    * [learnk8s troubleshooting flowchart](https://learnk8s.io/troubleshooting-deployments) → one visual map for "my Pod or Service doesn't work"
    * Kubernetes docs → [Debug Services](https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/) and [Debugging DNS Resolution](https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/)
* Write every incident as a short postmortem → symptom → investigation → root cause → fix → lesson

!!! tip "Quick revision"

    * Name fails, IP works → DNS | IP fails, Pod IP works → Service/ports | Pod IP fails → app
    * `describe svc` → Endpoints empty = selector/readiness/namespace | filled but refused = targetPort
    * DNS = `kube-dns` Service → CoreDNS Pods → must be Ready → must reach the API server through kube-proxy rules
    * CrashLoopBackOff → `kubectl logs --previous`
    * kind + "too many open files" → raise `fs.inotify.max_user_instances` / `max_user_watches` on the host, restart kube-proxy and CoreDNS

!!! question "Interview points"

    * A Pod can't resolve a Service name, how do you debug? → confirm the Service exists in that namespace, curl the ClusterIP to separate DNS from Service problems, check resolv.conf, check that CoreDNS Pods are Ready and read their logs
    * CoreDNS Pods show 0/1 Running, what does that mean? → the process runs but fails its readiness probe, so the kube-dns Service has no endpoints and DNS queries go unanswered
    * CoreDNS logs say plugin kubernetes not ready, why? → CoreDNS can't sync with the API server, often because kube-proxy rules for the kubernetes Service ClusterIP are missing on that node
    * How do you see why a container keeps crashing? → kubectl logs <pod> --previous shows the last crashed run
    * Why can kube-proxy crash with too many open files on kind? → kind nodes share the host kernel, and the default inotify instance limit is exhausted; raise fs.inotify limits with sysctl
    * Is it safe to delete a kube-proxy Pod? → yes, it's a DaemonSet Pod and is recreated immediately on the same node
    * Service Endpoints are filled but connections are refused? → targetPort doesn't match the port the app listens on
    * Service Endpoints are empty? → selector doesn't match Pod labels, Pods aren't Ready, or they're in another namespace
    * General debugging approach? → reproduce the exact error, split the path in half with tests, check get/describe/logs, compare healthy vs broken, go one layer down, fix, verify and document
