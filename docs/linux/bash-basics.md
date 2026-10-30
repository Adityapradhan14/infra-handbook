# Bash Basics

*Hands-on notes, from the BashGuide*

## Commands and arguments

* Bash splits a line on spaces → first word = command, rest = arguments
* `echo a   b` → 2 args → prints `a b`
* `echo "a   b"` → 1 arg → prints `a   b`
* Quotes decide how many arguments a command gets

## Types of commands

* Alias → text shortcut → `ll` = `ls -alF`
* Function → named block of bash code
* Builtin → inside bash itself → `cd`, `echo`, `read`
* Keyword → bash syntax → `if`, `for`, `while`, `[[`
* Executable → program file on disk → `/usr/bin/ls`
* `type cd` / `type -a ls` → shows which kind
* `cd` must be builtin → a separate program can't change your shell's directory
* Same name → alias wins, then keyword, function, builtin, executable

## `[` needs spaces

* `[` is a command → `[ $x = 5 ]` → args: `$x`, `=`, `5`, `]`
* `[$x = 5]` → bash looks for command named `[5` → not found

## Scripts and the shebang

* Shebang → `#!/usr/bin/env bash` → tells Linux which program reads the file
* Without it → may run under `sh`, bash features break
* `.sh` extension means nothing to Linux → first line decides
* `/usr/bin/env bash` → finds bash in `PATH` → more portable than `/bin/bash`
* Runnable needs → `chmod +x` + shebang → run with `./script.sh`
* `bash script.sh` → shebang ignored, bash already chosen

## Special characters

* `"..."` → expands `$var`, keeps spaces
* `'...'` → everything literal, no expansion
* `\` → escape next char
* `$` → expansion → `$var`, `$(cmd)`, `$((1+2))`
* `#` → comment
* `;` → run commands one after another
* `&&` → run next only if previous succeeded | `||` → run next only if previous failed
* `>` `<` `|` → redirect, input, pipe (see [Redirection & Pipes](redirection.md))
* `{ }` → group in same shell | `( )` → group in subshell
* `~` → home | `*` → any chars | `?` → one char

## Variables

* `name="aditya"` → no spaces around `=`
* `"$name"` → always quote
* `"${name}_bak"` → braces when text touches the name

## Special parameters

* `$0` → script name
* `$1` `$2` → arguments
* `$#` → number of arguments
* `"$@"` → all args, each kept separate → use this
* `"$*"` → all args glued into one string → only for messages
* `$?` → exit code of last command, `0` = success
* `$$` → PID of current shell

## Parameter expansion

* `${var:-default}` → default if empty/unset → `PORT=${PORT:-8080}`
* `${#var}` → length
* `${f%.gz}` → remove from end → `backup.tar.gz` → `backup.tar`
* `${f#backup.}` → remove from start → `backup.tar.gz` → `tar.gz`

!!! warning "Quoting danger"

    * `file='no secret'; rm $file` → runs `rm no secret` → deletes wrong file
    * `rm "$file"` → one argument → correct

## Arithmetic

* Variables are strings by default → `a=5; a+=2` → `52` (string append)
* `a=$((a + 2))` → `7`
* `let a+=2` → `7`
* `declare -i a=5; a+=2` → `7` → integer attribute, every assignment is math
* `a=5+2` → `"5+2"` text | `declare -i a=5+2` → `7`
* Prefer `$(( ))` and `(( ))` → `a=$((a+2))`, `(( a++ ))`

## Here documents

* `cat > file <<'EOF' ... EOF` → write many lines into a file at once
* Quoted `'EOF'` → no expansion inside → `$vars` written literally

```bash
cat > notes.txt <<'EOF'
line one
$HOME stays as text
EOF
```

!!! question "Interview points"

    * Shebang purpose → picks the interpreter → `#!/usr/bin/env bash` finds bash in `PATH`
    * `$@` vs `$*` → `"$@"` keeps each arg separate, `"$*"` glues them into one string
    * Why is `cd` a builtin → a separate program can't change your shell's directory
    * `a=5; a+=2` gives `52` → variables are strings → use `$(( ))` for math
