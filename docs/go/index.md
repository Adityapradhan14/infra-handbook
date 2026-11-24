# Go

Notes on Go, starting with what Go is and why it exists, then how Go is laid out on a machine before any language syntax: where it is installed, where it keeps downloads and caches, and how modules, packages and files fit together. Knowing these layers makes setup and build errors much easier to debug. Language chapters follow.

<div class="ih-chapters" markdown>

1. [What is Go](what-is-go.md)
    History, why it was built, compiled vs interpreted, single binary, goroutines, comparison with other languages, where it is used
2. [Installation & GOROOT](installation-and-goroot.md)
    Where Go lives, `PATH`, the toolchain behind `go`, `go.env`, duplicate installs
3. [GOPATH, Caches & go env](gopath-and-caches.md)
    `~/go/bin`, module cache, build cache, settings priority, cleaning caches
4. [Modules & Packages](modules-and-packages.md)
    `go mod init`, `go.mod`, folders as packages, `package main`, exported names
5. [Go Files, Running & Testing](files-running-testing.md)
    Parts of a `.go` file, `go run` / `go build`, reading compile errors, first test, linting
6. [Functions & Printing](functions.md)
    `Println` vs `Printf` verbs, parameters, multiple results, `(value, error)`, named returns
7. [Variables, Types & Constants](variables-types-constants.md)
    `var` and `:=`, zero values, type inference, basic types, conversions, `const`
8. [Loops & Conditionals](loops-and-conditionals.md)
    `for` in all its forms, `if` with short statements, `else`, `switch`, evaluation order, square-root exercise
9. [Defer](defer.md)
    Delayed calls for cleanup, arguments evaluated immediately, LIFO stacking

</div>
