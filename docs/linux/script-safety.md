# Script Safety

*Hands-on notes, from the BashGuide*

## set -euo pipefail

* `-e` → stop when a command fails
* `-u` → error on unset variable → stops `$dirr` typo becoming `rm -rf /*`
* `-o pipefail` → pipe fails if any part fails, not just last
* `-e` doesn't catch failures inside `if` or before `&&` `||` → safety net, not guarantee

## trap

* `trap 'cleanup' EXIT` → runs when script ends, even on failure
* Used to delete temp files / half-written archives

## mktemp

* `mktemp` → unique temp file | `mktemp -d` → temp dir

```bash
#!/usr/bin/env bash
set -euo pipefail

tmp=$(mktemp -d)
cleanup() { rm -rf "$tmp"; }
trap cleanup EXIT

tar -czf "$tmp/backup.tar.gz" "$HOME/notes"
```

## Pitfalls 1–5

* `for f in $(ls)` → use `for f in *`
* `cp $file $dst` → `cp -- "$file" "$dst"`
* Filenames starting with `-` → use `--` or `./*`
* `[ $foo = bar ]` → quote or use `[[ ]]`
* `cd $dir` → `cd "$dir" || exit 1`
* All the same rule → quote vars, globs not `ls`, handle failures

!!! question "Interview points"

    * `set -euo pipefail` flag by flag → `-e` stop on failure, `-u` error on unset var, `-o pipefail` pipe fails if any part fails
    * Does `set -e` catch everything → no, not inside `if` or before `&&` `||` → safety net, not guarantee
    * `trap cleanup EXIT` → cleanup runs even when the script fails
    * Common bash pitfalls → quote vars, globs not `ls`, handle failures
