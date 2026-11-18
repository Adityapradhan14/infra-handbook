# REST, gRPC & Protobuf

*Hands-on notes, how Kubernetes components talk to each other*

## Why this matters

* Kubernetes is a group of programs talking over the network → kubectl ↔ API server, API server ↔ etcd, kubelet ↔ containerd
* They use two styles → **REST** and **gRPC** → knowing which is used where helps when reading logs, debugging and building tools

## REST

* An architectural style built on HTTP
* **Resources** identified by URLs → `/users/42`, `/api/v1/namespaces/default/pods`
* **HTTP verbs** act on them → `GET` (read), `POST` (create), `PUT`/`PATCH` (update), `DELETE`
* Payload usually **JSON** → text, human-readable
* Easy to debug with `curl` or a browser, works everywhere
* Slower and heavier → text payloads repeat field names every time, JSON parsing costs CPU, mostly HTTP/1.1 (one request at a time per connection), no native streaming

## gRPC

* RPC framework from Google → RPC = **Remote Procedure Call** → call a function on another machine as if it were local → `client.GetUser(ctx, req)`
* Contract defined first in a `.proto` file → client and server code **generated** from it
* Runs over **HTTP/2** → many requests at once on one connection (multiplexing)
* Messages in **protobuf** → binary, compact, fast
* Native **streaming** → server streaming, client streaming, both directions at once
* Harder to debug → binary payloads, needs `grpcurl` instead of `curl`

## REST vs gRPC

| | REST | gRPC |
|---|---|---|
| Model | Resources + HTTP verbs | Calling functions |
| Payload | JSON (text) | Protobuf (binary) |
| Transport | HTTP/1.1 or HTTP/2 | HTTP/2 only |
| Contract | Optional (OpenAPI) | Required (`.proto`), strongly typed |
| Code generation | Optional | Built in, many languages |
| Streaming | Not native (needs SSE / WebSockets) | Native, all directions |
| Performance | Slower, bigger payloads | Faster, smaller payloads |
| Browser support | Native | Needs gRPC-Web proxy |
| Debugging | Easy (`curl`, browser) | Harder (`grpcurl`) |
| Caching | HTTP caching works | No native HTTP caching |

* REST → public APIs, browsers, mobile apps, third-party integrations, simplicity
* gRPC → internal service-to-service calls, low latency, high volume, streaming
* Common pattern → REST at the edge (public), gRPC inside (between microservices)

## Protobuf (Protocol Buffers)

* Google's format for **serializing** structured data → same job as JSON, but binary and schema-first

### How it works

1. Define the schema in a `.proto` file

```proto
syntax = "proto3";

message User {
  int32 id = 1;
  string name = 2;
  bool active = 3;
}
```

* `= 1`, `= 2`, `= 3` → **field numbers**, not values → they identify each field on the wire

2. Generate code → `protoc --go_out=. user.proto` → a Go struct `User` with encode/decode methods
3. Use it

```go
u := &pb.User{Id: 42, Name: "Aditya", Active: true}
data, _ := proto.Marshal(u)   // binary bytes
```

### Why it's smaller

* JSON → `{"id":42,"name":"Aditya","active":true}` → 39 bytes, field names sent every time
* Protobuf → only field number + type + value → about 12 bytes → both sides already have the schema, so names never travel
* Small integers use **varint** encoding → as little as 1 byte

### Key properties

* **Strongly typed** → wrong types fail at compile time, not at runtime
* **Faster** → no text parsing
* **Not human-readable** → need the `.proto` to decode
* **Schema evolution** → add new fields without breaking old clients (they ignore unknown field numbers)
* Rule → **never change or reuse a field number** → mark removed ones `reserved`

| | JSON | Protobuf |
|---|---|---|
| Format | Text | Binary |
| Schema | Optional | Required |
| Size | Larger | Several times smaller |
| Speed | Slower parsing | Faster |
| Readable | Yes | No |
| Browser-native | Yes | No |

## Where Kubernetes uses each

| Connection | Style |
|---|---|
| kubectl / users → API server | REST over HTTPS (JSON) |
| Internal clients → API server | REST, can use protobuf instead of JSON |
| API server → etcd | gRPC |
| Objects stored inside etcd | Protobuf |
| kubelet → containerd / CRI-O (CRI) | gRPC |
| kubelet → storage drivers (CSI) | gRPC |
| kubelet → device plugins (e.g. GPUs) | gRPC |

* `kubectl` is just a REST client → see the real HTTP calls:

```bash
kubectl get pods -v=8          # shows GET /api/v1/namespaces/default/pods
kubectl get --raw /api/v1/namespaces/default/pods | head -c 300
kubectl api-resources          # every resource type the REST API exposes
```

!!! tip "Quick revision"

    * REST = resources + verbs + JSON, easy and universal
    * gRPC = call functions, protobuf over HTTP/2, fast, typed, streaming
    * Protobuf = binary, schema-first, field numbers instead of names
    * Kubernetes: REST for its API, gRPC for etcd, CRI, CSI and device plugins

!!! question "Interview points"

    * REST vs gRPC? → REST is resource-oriented, JSON over HTTP, easy to debug and works everywhere, best for public APIs; gRPC is contract-first with protobuf over HTTP/2, faster, strongly typed and has native streaming, best for internal service calls
    * Why is gRPC faster? → binary protobuf payloads are smaller and cheaper to parse, and HTTP/2 multiplexes many calls over one connection
    * What is protobuf? → a binary, schema-first serialization format; you define messages in a .proto file and generate typed code, and field numbers replace field names on the wire
    * How does protobuf stay backward compatible? → old code ignores unknown field numbers; never reuse or change a field number, mark removed ones reserved
    * Is protobuf encryption? → no, it is only an encoding format
    * Where does Kubernetes use gRPC? → API server to etcd, and the kubelet to the container runtime (CRI), storage drivers (CSI) and device plugins
    * What protocol does kubectl use? → REST over HTTPS to the API server; -v=8 shows the requests
