# Keyboard Shortcuts

*From The Linux Command Line, chapter 8*

## Cursor Movement

* `Ctrl-A` → start of line
* `Ctrl-E` → end of line
* `Alt-F` / `Alt-B` → forward / back one word
* `Ctrl-L` → clear screen (same as `clear`)

## Editing

* `Ctrl-U` → delete everything before the cursor
* `Ctrl-K` → delete everything after the cursor
* `Ctrl-W` → delete the previous word
* `Alt-D` → delete the next word
* `Ctrl-Y` → paste back what was just deleted
* `Ctrl-_` → undo

## Completion

* `Tab` → complete a command, file or path
* `Tab Tab` → show all possible completions
* Works for commands, paths, `~user`, `$VAR`, and (with bash-completion) git/kubectl/terraform subcommands

## History

* `history` → list past commands; `history | grep docker` → search them
* `↑` / `↓` → previous / next command
* `Ctrl-R` → reverse search; type part of a command, `Ctrl-R` again for older matches, `Enter` to run, `Ctrl-G` to cancel
* `!!` → rerun the last command. `sudo !!` → rerun it with sudo
* `!$` → last argument of the previous command. `mkdir logs && cd !$`
* `Alt-.` → paste the last argument (press again for older ones)
* `!n` → run history entry number n. `!git` → last command starting with git
* History file → `~/.bash_history` (size set by `HISTSIZE` in ~/.bashrc)

## Process Control

* `Ctrl-C` → kill the running command (SIGINT)
* `Ctrl-Z` → pause it (SIGTSTP); `fg` resumes, `bg` runs it in background
* `Ctrl-D` → end of input; exits the shell if the line is empty

!!! tip "Quick revision"

    * `Ctrl-A`/`E` start/end | `Ctrl-U`/`K` delete before/after | `Ctrl-W` delete word
    * `Ctrl-R` search history | `!!` last command | `!$` / `Alt-.` last argument
    * `Tab Tab` completions | `Ctrl-C` kill | `Ctrl-Z` pause | `Ctrl-L` clear

!!! question "Interview points"

    * `Ctrl-C` sends SIGINT (stop); `Ctrl-Z` sends SIGTSTP (pause, resumable with `fg`).
    * `sudo !!` → fastest fix for "Permission denied".
    * Never put passwords or tokens on the command line; they're saved in `~/.bash_history`.
