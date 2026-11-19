# Installation & GOROOT

## What an install gives you

* Installing Go = one folder on disk → everything Go needs is inside it
* That folder = **GOROOT** ("Go's root") → standard location on Linux → `/usr/local/go`
* Inside it, three things that matter:
    * the `go` command → one program that builds, runs, tests, formats and downloads
    * the compiler and other tools that `go` calls internally
    * the **standard library source code** → `fmt`, `os`, `net/http` … as plain `.go` files

```bash
go version            # go version go1.27.4 linux/amd64 → version + OS/arch
go env GOROOT         # /usr/local/go
ls $(go env GOROOT)
```

## What's inside GOROOT

| Path | Purpose |
|---|---|
| `bin/` | `go` and `gofmt` → the only two commands called directly |
| `src/` | standard library source (`src/fmt`, `src/os`, …) |
| `pkg/tool/<os>_<arch>/` | internal tools `go` runs for you |
| `go.env` | Go's default settings |
| `VERSION` | version string |
| `api/`, `doc/`, `lib/`, `misc/`, `test/` | Go's own internals, ignore |

## The toolchain behind `go`

```bash
ls $(go env GOROOT)/pkg/tool/linux_amd64
# asm  cgo  compile  cover  fix  link  preprofile  vet
```

| Tool | Does |
|---|---|
| `compile` | turns `.go` files of one package into object code |
| `link` | joins all compiled packages into one binary |
| `asm` | assembles the few `.s` assembly files in the stdlib |
| `cgo` | lets Go call C code |
| `vet` | what `go vet` runs → finds suspicious code |
| `cover` | test coverage → `go test -cover` |
| `fix` | rewrites old code to newer APIs |
| `preprofile` | helper for profile-guided optimization |

* Never called directly → `go build` = `compile` each package, then `link`

## The standard library is just folders

```bash
ls $(go env GOROOT)/src/fmt
head -20 $(go env GOROOT)/src/fmt/print.go
```

* `src/fmt` = a folder of `.go` files, every one starting with `package fmt`
* Split across files only for organization → `print.go`, `scan.go`, `format.go`, `errors.go`
* `*_test.go` → test files, run by `go test`, left out of normal builds
* `doc.go` → holds only the package's documentation comment (common convention)
* `fmt` itself imports `io`, `os`, `strconv` … → stdlib = packages built from other packages
* `fmt.Println` works because `Println` starts with a capital letter → exported | lowercase names like `commaSpaceString` stay private to `fmt`

## How the shell finds `go`

* Typing `go` → shell checks folders listed in **PATH**, left to right, runs the **first** `go` found
* Go's `bin` not in PATH → `go: command not found` even though Go is installed
* Add to `~/.bashrc` (tarball install):

```bash
export PATH=$PATH:/usr/local/go/bin:$HOME/go/bin
```

```bash
which go                       # which go actually runs
echo $PATH | tr ':' '\n'       # PATH one folder per line
```

### ~/.profile vs ~/.bashrc

* `~/.profile` → runs **once at login** → everything opened afterwards inherits that PATH
* `~/.bashrc` → runs **every time a terminal opens** → appends on top of the inherited PATH
* Same folder added in both, or added twice → duplicates in PATH → harmless (first match wins) but confusing
* Changed `~/.profile` → log out and back in to see it | changed `~/.bashrc` → new terminal or `source ~/.bashrc`

## go.env: default settings

```bash
cat $(go env GOROOT)/go.env
```

* `GOPROXY=https://proxy.golang.org,direct` → libraries are downloaded from Google's module mirror first, straight from the source repo (e.g. GitHub) if that fails
* `GOSUMDB=sum.golang.org` → every downloaded library is checked against a public checksum database → tampered code is rejected
* `GOTOOLCHAIN=auto` → if a project's `go.mod` asks for a newer Go than installed, Go **downloads that version and uses it** → build may use a different version than `go version` shows

## Duplicate installs

* Two Go installs on one machine (e.g. snap + `/usr/local/go`) → classic trap → editor, script or CI may pick the other one → different version, different stdlib, confusing errors
* Keep exactly **one** install
* Snap installs → auto-update in the background, GOROOT path changes on every update (`/snap/go/<revision>`)
* Tarball in `/usr/local/go` → official method, matches docs, CI images and Dockerfiles

```bash
which go
ls /usr/local/go                     # exists? → second install
/usr/local/go/bin/go version
snap list go                         # installed via snap?
sudo snap remove go                  # remove the snap copy
hash -r                              # forget cached command locations
```

| Symptom | Cause | Fix |
|---|---|---|
| `go: command not found` after install | Go's `bin` not in PATH | add `/usr/local/go/bin` to PATH in `~/.bashrc` |
| `go version` shows an unexpected version | another install earlier in PATH, or a snap auto-update | `which go`, keep one install |
| `No such file or directory` for a binary that was moved or removed | bash cached the old location | `hash -r` or open a new terminal |
| Build uses a newer Go than `go version` | `GOTOOLCHAIN=auto` + `go.mod` asking for newer | expected; check the `go` line in `go.mod` |

!!! tip "Quick revision"

    * GOROOT = where Go is installed → tools + stdlib source
    * PATH decides which `go` runs → first match wins
    * `go build` = `compile` + `link`
    * One Go install per machine

!!! question "Interview points"

    * What is GOROOT? → the directory where Go itself is installed, holding the go command, compiler and linker, and the standard library source
    * What does go build actually run? → the compile tool for each package, then the link tool to produce one binary
    * How does the shell decide which go binary runs? → it searches the PATH directories in order and runs the first match; which go shows it
    * What is GOPROXY? → where Go downloads modules from; default is the proxy.golang.org mirror with direct as fallback
    * What does GOSUMDB do? → verifies downloaded modules against a public checksum database so tampered code is rejected
    * What does GOTOOLCHAIN=auto do? → downloads and uses a newer Go toolchain when a module's go.mod requires one
    * Why is having two Go installs a problem? → different tools can pick different versions, giving inconsistent builds and confusing errors
    * Why run hash -r? → bash caches command locations; after moving or removing a binary it clears that cache
