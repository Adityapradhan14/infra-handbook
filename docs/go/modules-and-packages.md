# Modules & Packages

## The two levels

* **Module** = one project → marked by a `go.mod` file at its root
* **Package** = one folder of `.go` files inside that project
* One module, many packages

```
demo/                  ← module (the project)
├── go.mod             ← once, at the top
├── main.go            ← package main
└── wow/
    └── nice/
        ├── nice.go    ← package nice
        └── extra.go   ← package nice (same folder → same package)
```

## Module: go mod init

```bash
mkdir demo && cd demo
go mod init demo
cat go.mod
```

```
module demo

go 1.27
```

* `go mod init` only creates **one text file**, `go.mod`
* `module demo` → the project's name, also the prefix for importing its packages
* `go 1.27` → Go version the code is written for → the toolchain uses it to pick language behaviour (e.g. Go 1.22 changed how `for` loop variables work), not just a label
* Without `go.mod` → `go build`, `go test`, `go run .` refuse:

```
go: go.mod file not found in current directory or any parent directory
```

* Analogy → `git init` marks a folder as a repo | `go mod init` marks a folder as a Go project | `npm init` → `package.json`
* Later, libraries you use get listed in `go.mod` with exact versions, plus a `go.sum` file with their checksums → same versions for everyone who clones the repo

### Naming the module

* Practice → any short name (`hello`, `demo`)
* Real project → the repo URL → `go mod init github.com/<user>/<repo>` → others can `go get` it

### One go.mod covers every subfolder

* Go looks **upward** from the current folder until it finds `go.mod` → nested folders belong to that module automatically
* Don't run `go mod init` in subfolders of a project
* Don't nest one project inside another (module inside module) → editor tooling (gopls) gets confused → keep separate projects **side by side**:

```
~/learn-go/
├── hello-world/   ← own go.mod
├── integers/      ← own go.mod
└── iteration/     ← own go.mod
```

## Package: one folder

* Every `.go` file starts with `package <name>` → says which group it belongs to
* Every file in one folder → **same** package name, otherwise compile error:

```
found packages nice (nice.go) and other (extra.go)
```

* Convention → package name = folder name (`math/rand/` → `package rand`)
* Files in the same package see each other's code directly, no import needed, even lowercase names → Go treats the folder as one combined unit

## package main vs library

| | `package main` + `func main()` | any other name (`package greet`) |
|---|---|---|
| What it is | runnable program | library |
| `go run .` | runs | `package demo/greet is not a main package` |
| How it's used | it is the program | imported by `main`, or checked with `go test` |

* Program starts at `func main()` inside `package main` → both must be named exactly `main`
* A library runs only when something imports and calls it

### One main per folder

* All files in a folder = one package → two `func main()` in one folder:

```
main redeclared in this block
```

* More than one program → more than one folder, usually under `cmd/`:

```
demo/
├── go.mod
├── cmd/
│   ├── server/main.go   ← program 1
│   └── cli/main.go      ← program 2
└── greet/greet.go       ← shared library
```

```bash
go run ./cmd/server
go run ./cmd/cli
```

* Same layout as Kubernetes → `cmd/kubectl`, `cmd/kubelet` … each `package main`, real logic in library packages

## Importing your own package

```go
// greet/greet.go
package greet

func Hello() string {
	return "hello from greet"
}
```

```go
// main.go
package main

import (
	"fmt"
	"demo/greet"
)

func main() {
	fmt.Println(greet.Hello())
}
```

* Import path = **module name** (from `go.mod`) + **folder path** → `"demo/greet"`
* Call as `<package name>.<Name>` → `greet.Hello()`
* Standard library → short paths (`"fmt"`, `"os"`) | your own or downloaded → full path

## Exported names

* **Capital first letter** → exported, usable from other packages → `Hello`, `fmt.Println`, `math.Pi`
* **Lowercase** → private to its own package → `greet.hello()` from `main` is an error
* No `public` / `private` keywords → capitalization is the whole system

| Symptom | Cause | Fix |
|---|---|---|
| `go.mod file not found` | not inside a module | `go mod init <name>` at the project root |
| `is not a main package` | `go run` on a library folder | run the folder with `package main`, or test it with `go test` |
| `found packages a and b` | files in one folder declare different packages | same `package` line in every file of a folder |
| `main redeclared in this block` | two `func main()` in one folder | one program per folder, use `cmd/<name>/` |
| `undefined: greet.hello` / not exported | lowercase name used from another package | capitalize it → `Hello` |
| Strange editor errors in nested projects | module inside another module | keep projects side by side |

!!! tip "Quick revision"

    * 1 project = 1 `go.mod` at the top
    * 1 folder = 1 package, every file says the same `package` name
    * 1 runnable folder = `package main` + 1 `func main()`
    * Import path = module name + folder | Capital = exported

!!! question "Interview points"

    * Module vs package in Go? → a module is a versioned project defined by go.mod; a package is one directory of .go files inside it
    * What does go mod init do? → creates go.mod with the module path and the Go version, marking the directory as a module root
    * What is go.sum for? → it records checksums of dependency versions so builds verify they get exactly the same code
    * How does Go find the module for a nested folder? → it walks up the directory tree to the nearest go.mod
    * What makes a Go program executable? → a package named main with a func main, the entry point
    * Can one directory hold two main functions? → no, a directory is one package; separate programs go in separate directories such as cmd/<name>
    * How is an import path for your own package formed? → module path from go.mod plus the package's directory path
    * How does Go control visibility? → identifiers starting with a capital letter are exported, lowercase ones are package-private
    * Why do real module paths look like URLs? → so go get can locate and download the code, e.g. github.com/user/repo
