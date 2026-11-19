# Go Files, Running & Testing

## Parts of a .go file

* Every file has the same three parts, always in this order:

```go
// 1. package → which folder-group this file belongs to
package main

// 2. imports → other packages this file uses
import (
	"fmt"
	"demo/greet"
)

// 3. code → functions, constants, variables, types
func main() {
	fmt.Println(greet.Hello())
}
```

* `package` → first line (comments above it allowed), exactly one per file
* `import` → single `import "fmt"` or grouped `import ( ... )` → `gofmt` keeps the group sorted
* Top level of a file holds only declarations → `func`, `const`, `var`, `type`
* Statements (printing, loops, `if`) live **inside functions** → `fmt.Println("hi")` at top level is an error
* Comments → `// one line` | `/* many lines */`

### Compiler rules that catch beginners

* Unused **import** → compile error, not a warning:

```
"os" imported and not used
```

* Unused **local variable** → compile error
* Unused **function** → allowed → defining a function doesn't run it, something must call it

## go run vs go build

```bash
go run hello.go      # compile + run one file, no binary left behind
go run .             # same for the whole package in this folder (preferred)
go build             # binary named after the module (module go-tour → ./go-tour)
go build -o hello .  # binary named hello
./hello
```

* `-o` = name of the **output binary** → `go build -o hello.go` tries to write the binary over the source file:

```
build output "hello.go" already exists and is not an object file
```

* `.` = the package in the current folder → prefer `go run .` / `go build .` over file names → keeps working once a package has several files
* Binary is **static** (~2 MB for hello world) → Go runtime bundled in, no dependencies → copy to any Linux amd64 machine and run, Go not needed there
* Why DevOps tooling is written in Go → kubectl, Terraform, Docker, Prometheus ship as single binaries
* Keep binaries out of Git → add the binary name to `.gitignore`

```bash
file hello       # ELF 64-bit LSB executable
ls -lh hello
```

## Reading compile errors

```
./hello.go:5:12: syntax error: unexpected name string, expected (
```

* `./hello.go` → file | `5` → line | `12` → column | then the message
* Example cause → `func Hello string {` → functions always need `()`, even with no inputs → `func Hello() string {`
* One mistake often causes follow-up errors on later lines → fix the **first** error, re-run

## First test

```go
// hello.go
package main

func Hello() string {
	return "Hello, world"
}
```

```go
// hello_test.go
package main

import "testing"

func TestHello(t *testing.T) {
	got := Hello()
	want := "Hello, world"

	if got != want {
		t.Errorf("got %q want %q", got, want)
	}
}
```

```bash
go test
```

* Test = code that checks other code → Go compares results instead of you reading output
* File name must end in `_test.go` → only compiled by `go test`
* Same `package` as the code under test → can call `Hello()` directly
* Function name must start with `Test` and take `t *testing.T` → `t` reports failures (`*` = pointer, covered later)
* `got := Hello()` → `:=` creates a variable and assigns it
* `!=` → not equal | `t.Errorf` → marks the test failed with a message
* `%q` → placeholder replaced by the value in double quotes → `got "Hello there" want "Hello, world"`
* Loop → write test → watch it **fail** → fix code → watch it **pass**
* Libraries have no `main` → tests are how their code gets run and checked

## Formatting and linting

* `gofmt -w .` / `go fmt ./...` → one standard format, no style debates → editors run it on save
* `go vet ./...` → built-in checks for suspicious code (wrong `Printf` verbs, copied locks)
* **golangci-lint** → runs `go vet` plus many more linters in one command → standard in CI for serious Go repos

```bash
curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/HEAD/install.sh | sh -s -- -b $(go env GOPATH)/bin
golangci-lint --version
golangci-lint run          # lint current module → "0 issues."
golangci-lint linters      # enabled / disabled linters
```

* Catches what the compiler doesn't, e.g. an ignored error:

```go
f, err := os.Open("file.txt")
f.Close()   // err never checked → crash if the open failed
```

| Linter | Catches |
|---|---|
| `errcheck` | errors that are ignored |
| `govet` | suspicious code |
| `staticcheck` | bugs, dead code, deprecated calls |
| `unused` | unused functions, variables, types |
| `ineffassign` | values assigned and never read |

## Editor (VS Code + Go extension)

* Extension installs `gopls` (language server) and other tools into `~/go/bin`
* Format on save is on by default
* `F12` → go to definition | `Shift+F12` → find usages | `F2` → rename across files | `Ctrl+Shift+R` → refactor menu | hover → signature and docs

| Symptom | Cause | Fix |
|---|---|---|
| `build output "x.go" already exists and is not an object file` | `-o` given a source file name | `-o` takes the binary name → `go build -o hello .` |
| `imported and not used` | import never used | remove it or use it |
| `syntax error: unexpected ..., expected (` | function declared without `()` | `func Name() type` |
| `non-declaration statement outside function body` | statement at top level | move it inside a function |
| Program output didn't change after adding a function | function never called | call it from `main` |
| `go test` → `no test files` | test file not named `*_test.go` | rename it |

!!! tip "Quick revision"

    * File = `package` → `import` → declarations
    * Unused import/variable = error, unused function = fine
    * `go run .` to run, `go build -o name .` to build a static binary
    * Tests: `*_test.go`, `func TestXxx(t *testing.T)`, `go test`

!!! question "Interview points"

    * What are the parts of a Go source file? → package clause, imports, then top-level declarations (func, const, var, type)
    * Why does Go fail on unused imports and variables? → to keep code clean and builds fast; unused code is treated as a likely mistake
    * go run vs go build? → go run compiles to a temporary binary and runs it; go build writes the binary to disk
    * Why is Go popular for DevOps tools? → it builds single static binaries with no runtime dependencies, easy to ship and cross-compile
    * How do you read a Go compile error location? → file:line:column, and fix the first error since later ones are often knock-on
    * What are the rules for a Go test? → file ends in _test.go, function starts with Test and takes *testing.T, run with go test
    * What does t.Errorf do? → reports a failure with a formatted message and lets the test continue
    * gofmt vs go vet vs golangci-lint? → gofmt formats, go vet runs built-in correctness checks, golangci-lint runs many linters including vet in one pass
    * What does errcheck catch? → returned errors that the code ignores
