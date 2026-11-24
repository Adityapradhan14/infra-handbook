# What is Go

## In one line

* Go → an open-source, **compiled**, **statically typed**, **garbage-collected** language built at Google for large networked server software
* Goals → **fast to compile, fast to run, simple to read, easy concurrency**
* Name → **Go** | "golang" → search-friendly name, from the old site golang.org (now go.dev) | mascot → the **gopher**

## The problem it was built to solve

In 2007 Google's engineers were hitting the same walls every day:

| Problem | What it looked like | Go's answer |
|---|---|---|
| Slow builds | large C++ programs took a very long time to compile → engineers waiting on builds | compiles in seconds → simple dependency model, no header files, unused imports are errors |
| Complex languages | C++ and Java had grown huge → many ways to do one thing → hard to read someone else's code | small language → 25 keywords, one loop, one official format (`gofmt`) |
| Many cores, everything networked | threads in older languages were heavy and error-prone | goroutines and channels built into the language |
| Huge teams, huge codebases | code had to be readable by thousands of engineers | explicit code, no hidden magic, strict tooling |
| Dependency hell in deployment | programs needed the right runtime and libraries on every server | one self-contained binary |

* Core idea → keep the **speed and safety of a compiled language** with the **ease of a scripting language**

## History

| When | Event |
|---|---|
| Sep 2007 | Robert Griesemer, Rob Pike and Ken Thompson start sketching Go at Google |
| Nov 10, 2009 | Go is announced publicly and open-sourced → the Go playground's clock is frozen at 2009-11-10 23:00 UTC for this reason |
| Mar 2012 | **Go 1.0** → comes with the **Go 1 compatibility promise** → code written for Go 1 keeps compiling on later Go 1.x releases |
| 2013 | **Docker** is released, written in Go |
| 2014 | **Kubernetes** is released, written in Go → Go becomes the language of cloud infrastructure |
| 2015 | **Go 1.5** → the compiler is rewritten in Go itself (no more C) → GC pauses drastically reduced |
| 2018 | **Go 1.11** → **modules** (`go.mod`) introduced → replaces the old GOPATH-only workflow |
| 2021 | **Go 1.16** → modules on by default |
| Mar 2022 | **Go 1.18** → **generics** added → the biggest language change since 1.0 |
| Ongoing | A new release every ~6 months (February and August) |

### The designers

* **Ken Thompson** → co-created Unix and the B language (C's predecessor) → co-designed UTF-8
* **Rob Pike** → Unix team at Bell Labs, Plan 9 → co-designed UTF-8 with Ken Thompson
* **Robert Griesemer** → worked on Google's V8 JavaScript engine and Java's HotSpot VM
* This is why Go feels like "C, cleaned up" → familiar syntax, minus the dangerous and complicated parts

## What kind of language Go is

| Property | Meaning | Why it matters |
|---|---|---|
| **Compiled** | `go build` turns source into native machine code | no interpreter at runtime → fast startup, fast execution |
| **Statically typed** | every value has a type fixed at compile time | type mistakes are caught by the compiler, not in production |
| **Garbage collected** | the runtime frees unused memory automatically | no manual `malloc`/`free` → no use-after-free or double-free bugs like C |
| **Memory safe (mostly)** | bounds-checked arrays and slices, no pointer arithmetic | out-of-range access stops the program instead of corrupting memory |
| **Single binary** | the Go runtime is bundled into the program | copy one file to a server and run it → no Go, no runtime, no `pip install` |
| **Cross-compiling** | `GOOS=linux GOARCH=arm64 go build` | build for any OS/CPU from your laptop |
| **Concurrency built in** | `go f()` starts a goroutine | thousands of concurrent tasks are cheap |
| **Opinionated tooling** | `go fmt`, `go vet`, `go test`, `go mod` ship with Go | every Go project is formatted, built and tested the same way |
| **Batteries-included stdlib** | HTTP, JSON, crypto, TLS, files, testing | a production web server needs zero third-party packages |

### Compiled vs interpreted

```
Python:  source.py ──► python interpreter reads it line by line at runtime
Go:      main.go  ──► go build ──► ./app (machine code) ──► CPU runs it directly
```

* Interpreted → needs the interpreter installed everywhere, slower, errors only show when that line runs
* Compiled → one build step up front → runs anywhere with the same OS/CPU, errors caught before running

### The single static binary

```bash
go build -o app .
ls -lh app          # one file, a few MB
scp app server:/usr/local/bin/
ssh server app      # runs, Go not installed on the server
```

* Pure Go programs are linked statically → no external `.so` libraries needed
* `CGO_ENABLED=0 go build` → guarantees no C dependencies → the usual setting for container images
* Result → tiny Docker images → `FROM scratch` or distroless + one binary

### Concurrency in one look

```go
go fetch("https://a.com")   // runs at the same time
go fetch("https://b.com")   // runs at the same time
```

* **Goroutine** → a function running concurrently, managed by the Go runtime → starts with a stack of a few KB → you can run thousands
* **Channel** → a pipe for goroutines to send data to each other safely
* Motto → "Don't communicate by sharing memory; share memory by communicating."
* OS threads cost far more memory and setup → the Go scheduler multiplexes many goroutines onto a few OS threads

## Go compared with other languages

| | Python | Java | C / C++ | **Go** |
|---|---|---|---|---|
| Execution | interpreted | bytecode on JVM | native | **native** |
| Speed | slow | fast (after JVM warm-up) | fastest | **fast** |
| Typing | dynamic → checked at runtime | static | static | **static** |
| Memory | GC | GC | manual | **GC** |
| Startup time | medium | slow (JVM) | instant | **instant** |
| Deploy needs | Python + packages | a JVM | binary + shared libs | **one binary** |
| Compile time | none | medium | slow | **very fast** |
| Concurrency | limited by the GIL | threads | threads | **goroutines + channels** |
| Language size | small | large | very large | **small** |

* vs **Python** → Go is much faster, typed, ships as one file → Python is quicker for small scripts and data work
* vs **Java** → no JVM, no classes, far less boilerplate, instant startup
* vs **C/C++** → memory safe, garbage collected, much simpler, faster to compile → slightly slower, less low-level control
* vs **Rust** → Go is simpler and faster to learn, uses a GC → Rust has no GC and stricter safety guarantees, but a much steeper learning curve

## What Go deliberately leaves out

| Missing | What Go uses instead |
|---|---|
| Classes and inheritance | **structs** + **methods** + **interfaces** (composition) |
| Exceptions (`try/catch`) | functions return an `error` → `if err != nil { … }` |
| `while`, `do-while` | `for` in all its forms |
| Ternary `x ? a : b` | a normal `if / else` |
| Function overloading | different function names |
| Implicit type conversion | explicit `float64(x)` |
| Unused imports/variables | compile error → keeps code clean |
| Many code styles | one style enforced by `gofmt` |

* Trade-off → more lines in places, but **any Go code is readable by any Go developer**
* Go proverb → "Clear is better than clever."

## The 25 keywords

```
break     default      func    interface  select
case      defer        go      map        struct
chan      else         goto    package    switch
const     fallthrough  if      range      type
continue  for          import  return     var
```

* Java has 50+ and C++ 90+ → the whole language fits in your head

## Where Go is used

| Area | Written in Go |
|---|---|
| Containers | Docker, containerd, runc, Podman, Buildah |
| Kubernetes | kube-apiserver, kubelet, kube-scheduler, kubectl, etcd, CoreDNS, Helm, kind, k3s |
| Infrastructure as Code | Terraform and its providers, Pulumi's engine, OpenTofu |
| Observability | Prometheus, Grafana backend, Loki, Tempo, Jaeger, Thanos |
| Service mesh & networking | Istio control plane, Linkerd control plane, Traefik, Caddy, Cilium (control plane) |
| Security & secrets | Vault, Consul, Trivy, cosign |
| CI/CD & GitOps | Argo CD, Flux, Drone, Tekton |
| CLIs & dev tools | GitHub CLI (`gh`), Hugo, `k9s`, `lazygit` |
| Companies | Google, Uber, Cloudflare, Twitch, Dropbox, Monzo |

### Why Go won cloud infrastructure

* Infra tools must run on thousands of machines → **single binary** = no install headaches
* They talk over the network all day → **stdlib HTTP/gRPC** + **goroutines**
* They must be fast and use little memory → **compiled**, small footprint
* Many contributors across companies → **simple, uniform code** is easy to review
* Kubernetes chose Go → the whole cloud-native ecosystem (operators, controllers, CRDs, client libraries) followed

### Why Go matters for DevOps / SRE

* **Read the source** of Kubernetes, Docker or Terraform when the docs don't explain a behaviour
* **Write Kubernetes operators and controllers** → `client-go`, `controller-runtime`, Kubebuilder
* **Write Terraform providers** and Prometheus exporters
* **Build internal CLI tools** → ship one binary to the whole team
* Replace fragile long Bash scripts with typed, tested programs

## Where Go is not the best fit

* Quick one-off scripts and text munging → Bash or Python are faster to write
* Data science and ML → Python's ecosystem dominates
* Hard real-time or kernel-level code → C or Rust (no GC pauses)
* Desktop GUIs and mobile apps → other languages have far better tooling

| Myth | Reality |
|---|---|
| "Go is Google's internal language" | open source, governed in the open, used everywhere |
| "GC makes Go slow" | GC pauses are typically well under a millisecond → fine for servers |
| "No generics" | generics since Go 1.18 (2022) |
| "Go is only for web servers" | CLIs, infra tools, networking, databases (CockroachDB), operators |
| "Go and golang are different" | same language → "golang" is just the searchable name |

!!! tip "Quick revision"

    * Go → compiled, statically typed, garbage collected, built at Google (2007), public 2009, Go 1.0 in 2012
    * Created by Griesemer, Pike, Thompson → to fix slow builds, complexity and poor concurrency
    * Ships as one static binary → no runtime needed on the server
    * Goroutines + channels → cheap built-in concurrency
    * 25 keywords, no classes, no exceptions, no while → errors are values
    * Docker, Kubernetes, Terraform, Prometheus, etcd, Helm are all written in Go

!!! question "Interview points"

    * Who created Go and when? → Robert Griesemer, Rob Pike and Ken Thompson at Google, started in 2007, open-sourced in 2009, Go 1.0 in 2012
    * Why was Go created? → slow C++ builds, overly complex languages, and the need for easy concurrency on multicore networked servers at Google scale
    * Is Go compiled or interpreted? → compiled to native machine code
    * Why is Go popular for DevOps and cloud tools? → single static binaries, fast startup, low memory use, strong networking stdlib and built-in concurrency
    * Why does a Go binary run on a server without Go installed? → the runtime and dependencies are linked into the binary
    * What is a goroutine? → a lightweight function running concurrently, managed by the Go runtime rather than the OS, with a small growable stack
    * What is the Go 1 compatibility promise? → programs written for Go 1 continue to compile and run on later Go 1.x releases
    * How does Go handle errors without exceptions? → functions return an error value that the caller checks with if err != nil
    * Does Go support object-oriented programming? → partly: structs with methods and interfaces, but no classes or inheritance; it favours composition
    * When were generics added to Go? → Go 1.18, in 2022
    * Name tools written in Go → Docker, Kubernetes, Terraform, Prometheus, etcd, Helm, Vault
    * Go vs Python for infra tooling? → Go is faster, typed and ships as one binary; Python is quicker for small scripts and data work
