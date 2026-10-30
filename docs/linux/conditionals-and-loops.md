# Conditionals, Loops & Functions

*Hands-on notes, from the BashGuide*

## Exit status

* Every command returns `0`–`255` → `0` = success, else failure
* `echo $?` → see last exit code
* `exit 1` in scripts when something goes wrong
* Exit codes are `0`–`255` → `ping`: `0` reply, `1` no reply, `2` other error
* `>&2` → send message to stderr → all error messages go there
* `! cmd` → flips exit status → `! grep -q bad file`
* `grep -q` → no output, just exit code → used in conditions

## `&&` and `||`

* `mkdir d && cd d` → `cd` only if `mkdir` worked
* `cd "$dir" || { echo "no dir" >&2; exit 1; }` → stop script if `cd` fails
* `{ ...; }` groups commands → needs `;` before `}`
* `;` vs `&&` → `;` runs next always, `&&` only on success
* `a && b && c || d` → `d` runs if ANY earlier one failed → group: `a && { b || d; }`

## if

* `if [[ cond ]]; then ... elif [[ cond ]]; then ... else ... fi`

```bash
if [[ -f "$file" ]]; then
    echo "exists"
elif [[ -d "$file" ]]; then
    echo "is a dir"
else
    echo "missing"
fi
```

## `[` vs `[[`

* `[` → command, unquoted vars get split → breaks on spaces/empty
* `[[` → bash keyword, no splitting → safe, supports patterns + regex
* In bash scripts always use `[[ ]]`
* `[ apple < banana ]` → `<` is redirection → use `[[ ]]` or `\<`

## Tests

* Files → `-e` exists | `-f` file | `-d` dir | `-r` readable | `-w` writable | `-x` executable | `-s` not empty
* `-h file` → true if symlink
* `f1 -nt f2` → `f1` newer | `-ot` → older
* `[[ $var ]]` → true if var not empty | `[[ ! $var ]]` → true if empty
* Strings → `-z` empty | `-n` not empty | `=` `!=` compare
* Numbers → `-eq` `-ne` `-lt` `-gt` `-le` `-ge` → or `(( n > 5 ))`
* Strings vs numbers → `"314" < "9"` as text, but `314 -gt 9` as numbers
* `[[ $f == *.log ]]` → pattern
* `[[ $u =~ ^[a-z]+$ ]]` → regex
* `[[ $x = $pat ]]` unquoted right side → pattern match | `"$pat"` quoted → exact string

## Loops

* `for f in *.log; do ...; done` → loop files → never `$(ls)`
* `for i in {1..5}; do ...; done`
* `for (( i=0; i<5; i++ ))` → C-style loop
* `while read -r line; do ...; done < file` → read line by line
* `read -r` → don't treat `\` as escape → always use `-r`
* `until cmd` → loop while `cmd` fails → same as `while ! cmd`
* `break` → exit loop | `continue` → next iteration
* `select` → simple menu → rarely used

## case

* `case $1 in start) ... ;; stop) ... ;; *) usage ;; esac`
* `;&` → fall through to next block

```bash
case $1 in
    start) echo "starting" ;;
    stop)  echo "stopping" ;;
    *)     echo "usage: $0 start|stop" ;;
esac
```

## Functions

* `name() { ...; }`
* Inside function → `$1` `$@` are the function's args
* `local var=x` → variable stays inside function
* `return 0/1` → function exit code | `exit` → ends whole script

!!! question "Interview points"

    * `[` vs `[[` → `[` is a command with word splitting, `[[` is a keyword without it
    * `a && b || c` → `c` also runs if `b` fails → not a real if/else
    * `return` vs `exit` → `return` ends the function, `exit` ends the whole script
    * Why never `for f in $(ls)` → filenames with spaces split → use `for f in *`
