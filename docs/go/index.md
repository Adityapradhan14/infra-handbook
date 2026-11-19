# Go

Notes on Go, starting from how Go is laid out on a machine before any language syntax: where it is installed, where it keeps downloads and caches, and how modules, packages and files fit together. Knowing these layers makes setup and build errors much easier to debug. Language chapters follow.

<div class="ih-chapters" markdown>

1. [Installation & GOROOT](installation-and-goroot.md)
    Where Go lives, `PATH`, the toolchain behind `go`, `go.env`, duplicate installs
2. [GOPATH, Caches & go env](gopath-and-caches.md)
    `~/go/bin`, module cache, build cache, settings priority, cleaning caches
3. [Modules & Packages](modules-and-packages.md)
    `go mod init`, `go.mod`, folders as packages, `package main`, exported names
4. [Go Files, Running & Testing](files-running-testing.md)
    Parts of a `.go` file, `go run` / `go build`, reading compile errors, first test, linting

</div>
