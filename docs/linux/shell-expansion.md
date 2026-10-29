# Expansion & Quoting

*From The Linux Command Line, chapter 7*

* Expansion → The shell rewrites your command BEFORE running it. The program only sees the result.
* `echo` shows what a command expands to → `echo *.txt`
* Order → brace → tilde → parameter, command, arithmetic → word splitting → pathname (glob)

## Pathname Expansion (Globbing)

* `*` → zero or more characters. `ls *.txt`
* `?` → exactly one character. `ls file?.txt`
* `[abc]` → one character from the set. `ls file[123].txt`
* `[a-z]` / `[0-9]` → one character from a range.
* `[!abc]` → one character NOT in the set.
* `[[:digit:]]` `[[:upper:]]` `[[:alpha:]]` → character classes.
* Done by the shell, not the command: `ls *.txt` runs as `ls a.txt b.txt`.
* `*` skips hidden files (dotfiles); `.*` matches them.
* No match → the pattern stays as plain text. `ls *.xyz` → `ls: cannot access '*.xyz'`

## Tilde Expansion

* `~` → your home directory. `cd ~`
* `~user` → that user's home. `cd ~ganesh`
* Not expanded inside quotes: `echo "~"` prints `~`.

## Brace Expansion

* `{a,b,c}` → makes one word per item. `echo file{1,2,3}` → `file1 file2 file3`
* `{1..5}` → sequence. `echo {1..5}` → `1 2 3 4 5`
* `{a..e}`, `{01..10}` (zero-padded), `{1..10..2}` (step 2)
* Real use → `mkdir -p proj/{src,docs,tests}` | `cp app.conf{,.bak}` → backup copy
* Not a glob: creates names whether or not files exist.

## Parameter Expansion

* `$name` → value of the variable. `name="Aditya"; echo $name`
* `${name}` → explicit form; needed next to text. `echo ${name}_logs`
* `$name_logs` → looks for a variable called `name_logs` (empty).
* `printenv` / `set` → list variables.

## Command Substitution

* `$(cmd)` → replaced by the command's output. `echo "Today is $(date)"`
* `` `cmd` `` → old syntax; `$(...)` preferred (nests, easier to read).
* Real use → `kill $(pgrep sleep)` | `cd $(dirname $(which python3))`

## Arithmetic Expansion

* `$((expr))` → integer maths. `echo $((5 + 3))` → `8`
* Operators → `+ - * / % **`
* Integers only: `$((5 / 2))` → `2` (no decimals; use `bc` for those).
* Variables need no `$` inside: `x=4; echo $((x * 2))`

## Word Splitting

* Unquoted expansions are split on spaces/tabs/newlines into separate words.
* `f="my file.txt"; rm $f` → tries to delete `my` and `file.txt` ❌
* `rm "$f"` → deletes `my file.txt` ✅
* Rule: always quote variables → `"$var"`

## Quoting

* Double quotes `"..."` → stop word splitting and globbing; `$`, `$( )`, `$(( ))` and `\` still work.
    * `echo "$HOME has *"` → `/home/ganesh has *`
* Single quotes `'...'` → stop ALL expansion; everything is literal.
    * `echo '$HOME has *'` → `$HOME has *`
* `\` → escapes one character. `echo \$HOME` → `$HOME` | `rm my\ file.txt`
* `\` inside double quotes only escapes `$`, `` ` ``, `"`, `\` and newline.
* Can't put `'` inside single quotes; use `"it's"` instead.

!!! tip "Quick revision"

    * `*` any | `?` one | `[abc]` set | `[!abc]` not set
    * `~` home | `{a,b}` list | `{1..5}` sequence
    * `$var` / `${var}` value | `$(cmd)` output | `$((...))` integer maths
    * `"..."` expands `$` only | `'...'` nothing expands | `\` one character

!!! question "Interview points"

    * The shell expands the command first; the program never sees `*`, `~` or `$var`.
    * Globbing is done by the shell → why `find . -name *.txt` breaks; quote it: `find . -name "*.txt"`
    * Single vs double quotes: single = fully literal, double = variables still expand.
    * Always quote variables (`"$var"`) to avoid word splitting on spaces.
    * Brace expansion makes names; globbing matches existing files.
