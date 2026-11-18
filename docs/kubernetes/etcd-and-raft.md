# etcd & Raft

## What etcd is

* Distributed **key-value store** → stores data as key → value pairs, like a giant dictionary
* Kubernetes keeps its entire state here → every Deployment, Pod, Service, Secret, ConfigMap, node
* Keys look like paths → `/registry/deployments/default/web`, `/registry/pods/kube-system/coredns-xxxx`
* Desired state + current status of the whole cluster = the cluster's single source of truth
* Only the API server talks to etcd → everyone else goes through the API server
* Name → `/etc` (Linux config folder) + `d` for distributed

## Why it matters so much

* Lose etcd without a backup = lose the cluster's memory → nodes keep running Pods, but Kubernetes no longer knows what should exist
* So in production → run 3 or 5 etcd members + take regular snapshots

```bash
ETCDCTL_API=3 etcdctl snapshot save /backup/etcd.db    # backup (needs certs/endpoints on a real cluster)
etcdctl snapshot status /backup/etcd.db -w table
```

## How etcd stores data

### Write-Ahead Log (WAL)

* Every change is first written to a **log on disk**, before it is applied
* If etcd crashes or the power goes → replay the log → nothing lost, changes stay in the right order
* Same idea as a bank writing every transaction in a ledger before updating balances

### Protobuf, not JSON

* Kubernetes objects are stored in etcd as **Protocol Buffers** → compact binary format
* Smaller and faster than JSON → stays quick even with thousands of objects
* Protobuf is **not encryption** → just a space-efficient format → see [REST, gRPC & Protobuf](rest-grpc-protobuf.md)

### Not encrypted by default

* etcd stores data **in plain form** unless encryption at rest is turned on
* Secrets are only **base64-encoded** → base64 is encoding, not encryption → anyone who reads etcd's files can decode them
* Production → enable **encryption at rest** in the API server config (`EncryptionConfiguration`, ideally with a KMS provider)
* Also → restrict who can reach etcd, use TLS between API server and etcd

```bash
echo 'cGFzc3dvcmQxMjM=' | base64 -d     # password123 → base64 hides nothing
```

## Raft: keeping copies in agreement

* Problem → one etcd copy = single point of failure | 3 copies = how do they stay identical? If two writes arrive at two copies at the same time, which wins?
* **Raft** = consensus algorithm → the rulebook that lets several machines agree on the same data, even if some crash
* Analogy → 5 students keeping one shared notebook:
    1. **One leader** (class monitor) → only the monitor writes new entries | everyone else is a **follower**
    2. **All writes go through the leader** → anyone with a new entry hands it to the monitor
    3. **Leader asks for agreement** → "adding entry #42" → followers write it and reply "done"
    4. **Majority = committed** → once 3 of 5 have it, it's official
    5. **Leader disappears** → followers stop hearing from it → one says "vote for me" → whoever gets a majority becomes the new leader (**leader election**)

### The three states

| State | Role |
|---|---|
| Leader | Accepts writes, copies them to followers, sends regular **heartbeats** ("I'm alive") |
| Follower | Copies what the leader sends, votes in elections |
| Candidate | A follower that stopped getting heartbeats and is asking for votes |

### Quorum

* **Quorum = majority = (N / 2) + 1** (rounded down, then +1)

| etcd members | Quorum | Failures it survives |
|---|---|---|
| 1 | 1 | 0 |
| 2 | 2 | 0 |
| 3 | 2 | 1 |
| 4 | 3 | 1 |
| 5 | 3 | 2 |

* Use **odd numbers** (3 or 5) → a 4th member costs more but survives no extra failure
* Bigger isn't always better → every write waits for a majority → 7+ members slow writes down
* **Quorum lost** (e.g. 2 of 3 down) → etcd stops accepting writes → Kubernetes can't create, change or delete anything → running Pods keep running, but the cluster is frozen

### Split-brain

* Network splits 5 members into a group of 3 and a group of 2
* Group of 3 has a majority → elects a leader, keeps working
* Group of 2 can't reach a majority → can't accept writes
* So there are **never two leaders writing different data** (that failure is called split-brain) → majority voting prevents it

```bash
etcdctl member list
etcdctl endpoint status --cluster -w table     # shows which member is leader
kubectl -n kube-system get pods | grep etcd    # kind: one etcd Pod on the control-plane node
```

!!! tip "Quick revision"

    * etcd = key-value store holding all cluster state, only the API server talks to it
    * WAL first, protobuf format, not encrypted by default (Secrets are just base64)
    * Raft = one leader, majority commit, re-election if the leader dies
    * Quorum = N/2 + 1 → use 3 or 5 members

!!! question "Interview points"

    * What is etcd? → a distributed, consistent key-value store that holds all Kubernetes cluster state; only the API server talks to it
    * What happens if you lose etcd with no backup? → the cluster loses its record of what should exist; you restore from an etcd snapshot
    * Are Kubernetes Secrets encrypted? → not by default; they are base64-encoded in etcd, so you enable encryption at rest (ideally with KMS) and restrict etcd access
    * What is Raft? → a consensus algorithm: one elected leader takes writes and replicates them, a write commits once a majority acknowledges it, and followers elect a new leader if the leader fails
    * What is quorum and why odd numbers? → a majority, N/2+1; 4 members tolerate the same single failure as 3, so even numbers add cost without extra safety
    * What happens when etcd loses quorum? → it stops accepting writes, so the Kubernetes API can't make changes; existing Pods keep running
    * How does Raft prevent split-brain? → only a side with a majority can elect a leader and commit writes, so two leaders can never both write
    * What is the WAL? → the write-ahead log: every change is logged to disk before being applied, so etcd can replay it after a crash
