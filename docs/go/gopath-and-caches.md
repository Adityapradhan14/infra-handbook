# GOPATH, Caches & go env

## GOROOT vs GOPATH

* GOROOT → **Go's** own files (the install)
* GOPATH → Go's **storage for you** → tools you install + libraries it downloads → default `~/go`, created on first use
* Your own code → **not** in GOPATH → any folder works (`~/learn-go`, `~/projects/...`)

```
/usr/local/go   → Go itself                    (GOROOT)
~/go            → installed tools + downloads   (GOPATH)
~/anywhere      → your code
```

## Inside ~/go

```
~/go/
├── bin/                     ← binaries from `go install`
└── pkg/
    └── mod/                 ← module cache: every downloaded library
        ├── github.com/...
        ├── golang.org/...
        └── cache/download/  ← raw zip files they came from
```

* `~/go/bin` → e.g. `golangci-lint`, `gopls` (VS Code's language server), `staticcheck`, `kind` → each a single self-contained binary
* `~/go/pkg/mod` → folders named by **URL** → a module's name is where its code lives → that's how `go get` knows where to download from
* Version is part of the folder name → `kind@v0.33.0` → several versions of one library sit side by side
* Files are **read-only** → can't accidentally edit a library
* Tools installed with `go install` pull in their dependencies → module cache fills up even if you never downloaded anything yourself

## Build cache

* `~/.cache/go-build` → **GOCACHE** → compiled results of every package built
* Second build is fast → unchanged packages aren't recompiled
* Also caches test results → `go test` prints `(cached)` when nothing changed
* Safe to delete → builds just get slower once

## Variables at a glance

| Variable | Default | Used for |
|---|---|---|
| `GOROOT` | `/usr/local/go` | compiler + stdlib |
| `GOPATH` | `~/go` | root for the next two |
| `GOBIN` | empty → `$GOPATH/bin` | where `go install` puts binaries |
| `GOMODCACHE` | `$GOPATH/pkg/mod` | downloaded libraries |
| `GOCACHE` | `~/.cache/go-build` | build and test cache |
| `GOENV` | `~/.config/go/env` | your saved settings (`go env -w`) |

```bash
go env                                       # every setting
go env GOPATH GOBIN GOMODCACHE GOCACHE GOENV # specific ones
du -sh ~/.cache/go-build                     # build cache size
```

## Where a setting comes from

* Priority, lowest to highest:
    1. `$GOROOT/go.env` → Go's defaults
    2. `~/.config/go/env` → written by `go env -w KEY=value`
    3. environment variables (`export GOBIN=...`) → win over everything
* `go env KEY` shows the **final** value, not where it came from
* Value set but not in `~/.config/go/env` → it's an environment variable → `echo $KEY`, then `grep` the shell startup files

```bash
go env -w GOBIN=$HOME/go/bin   # save a setting
go env -u GOBIN                # remove a saved setting
cat $(go env GOENV)            # saved settings
```

## Why GOPATH still exists

* Before Go 1.11 (2018) → **all** code had to live in `~/go/src` → imports resolved only from there
* Modules (default since Go 1.16) removed that rule → project root is wherever `go.mod` is
* Today `~/go` only holds installed tools and downloads → creating `~/go/src` by hand is not needed

## Cleaning

```bash
go clean -cache        # wipe build cache (GOCACHE)
go clean -testcache    # forget cached test results
go clean -modcache     # wipe module cache, re-downloaded on next build
```

| Symptom | Cause | Fix |
|---|---|---|
| Tool installed with `go install` → `command not found` | `~/go/bin` not in PATH | add `$HOME/go/bin` to PATH |
| Stale or odd build behaviour | corrupted build cache | `go clean -cache` |
| A downloaded library looks broken | corrupted module cache | `go clean -modcache` |
| `go test` prints `(cached)` and didn't re-run | nothing changed since last run | `go test -count=1` or `go clean -testcache` |
| "Why is Go using this value?" | env var overrides saved settings and defaults | `go env KEY`, `echo $KEY`, `cat $(go env GOENV)` |

!!! tip "Quick revision"

    * GOROOT = Go itself | GOPATH (`~/go`) = tools + downloads, not your code
    * `~/go/bin` = installed tools | `~/go/pkg/mod` = libraries, named by URL@version
    * `~/.cache/go-build` = build cache
    * defaults < `go env -w` < environment variables

!!! question "Interview points"

    * GOROOT vs GOPATH? → GOROOT is where Go is installed; GOPATH (default ~/go) holds installed binaries and the module cache
    * Does your code need to live in GOPATH? → no, since modules your project can be anywhere; go.mod marks the project root
    * Where does go install put binaries? → GOBIN, which defaults to $GOPATH/bin
    * What is the module cache? → $GOPATH/pkg/mod, read-only copies of downloaded modules stored by path and version
    * What is GOCACHE? → the build cache of compiled packages and test results that makes rebuilds fast
    * Setting precedence in Go? → environment variables override go env -w settings, which override the go.env defaults
    * How do you force tests to re-run? → go test -count=1 or go clean -testcache
    * Why are module names URLs? → the path tells Go where to fetch the code from
