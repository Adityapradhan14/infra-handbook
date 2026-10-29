# Redirection & Pipes

*From The Linux Command Line, chapter 6*

* Redirection → Changes where a command's input, output, or errors go.
* The shell sets it up before the command runs; the command never knows.

## 3 standard streams

* `0` stdin → input (keyboard)
* `1` stdout → normal output (terminal)
* `2` stderr → error messages (terminal)

## Output

* `>` → stdout to file, overwrites (creates if missing). `ls > out.txt`
* `>>` → stdout to file, appends. `echo hi >> out.txt`
* `> file` → empties the file (clear a log).
* Shell truncates BEFORE the command runs: `sort f > f` leaves f EMPTY.
* `set -o noclobber` → blocks overwriting; `>|` forces it.

## Errors

* `2>` → stderr to file. `find / -name x 2> err.log`
* `2>>` → stderr to file, appends.
* Split → `cmd > out.log 2> err.log`

## Both together

* `2>&1` → `2` stderr, `>` send to, `&1` wherever stdout points RIGHT NOW.
* `&` = "1 is a stream, not a file". `2>1` creates a file named `1`.
* By default 1 and 2 both point at the screen (terminal).
* `2>&1` copies stdout's current destination once; it doesn't follow it later (like copying an address before someone moves house).
* `cmd > f 2>&1` → 1 moves to f, then 2 copies it → both in file ✅
* `cmd 2>&1 > f` → 2 copies screen, then 1 moves to f → errors on screen ❌
* Rule: put `2>&1` LAST.
* `&>` / `&>>` → Bash shorthand for both (overwrite / append). Fails in sh/dash (cron); portable form is `> f 2>&1`.

## /dev/null

* Discards everything written to it.
* `cmd 2> /dev/null` → hide errors | `cmd > /dev/null 2>&1` → hide everything (cron)

## Input

* `<` → stdin from file. `wc -l < f` → count only, no filename.

## Pipes

* `|` → stdout of one = stdin of next. Both run at the same time. `ls | grep .txt`
* stderr is NOT piped → `cmd 2>&1 | grep err` or `cmd |& grep err`

## tee

* `tee` → writes to screen AND file. `ls | tee out.txt` (`-a` appends)
* `sudo echo x > /etc/f` → Permission denied; `echo x | sudo tee /etc/f` → works.
* Why: `>` runs as YOU before sudo starts; tee opens the file itself, as root.

## Filters

* `cat a b > c` → join files
* `sort` → `-n` numeric, `-r` reverse, `-rn` largest first
* `uniq` → removes ADJACENT duplicates (sort first); `-c` counts, `-d` only dupes
* `wc -l` → lines (`-w` words, `-c` bytes)
* `grep x` → matching lines; `-v` non-matching, `-i` ignore case
* `head -n 5` / `tail -n 5` → first / last 5; `tail -f log` → follow live
* Top 5 lines → `sort f | uniq -c | sort -rn | head -5`
* Top 5 IPs → `awk '{print $1}' access.log | sort | uniq -c | sort -rn | head -5`

!!! question "Interview points"

    * Redirection is set up by the shell before the command starts.
    * Pipe connects stdout → stdin; stderr needs 2>&1.
    * `> f 2>&1` works, `2>&1 > f` doesn't (left to right).
    * `sudo echo > /etc/f` fails; use `| sudo tee`.
    * Never redirect into the file you're reading.
