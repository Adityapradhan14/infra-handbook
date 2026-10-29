# Working with Commands

*From The Linux Command Line, chapter 5*

* Command → An instruction given to the shell to perform an operation.

## 4 kinds of commands

* Executable → a file on disk (`mv` → /usr/bin/mv)
* Builtin → part of bash itself, no file (`cd`, `type`, `alias`, `help`)
* Alias → a shortcut (`ls` → `ls --color=auto`)
* Function → a small script loaded into the shell

## Finding Commands

* `type command` → Shows what kind of command it is (works for all 4). Best tool.
    * `type cd` → cd is a shell builtin
    * `type ls` → ls is aliased to 'ls --color=auto'
* `type -a command` → Shows every match (alias, builtin and file), in the order bash checks them.
* `which command` → Path of the executable being used.
    * `which python3` → /usr/bin/python3
    * Prints nothing for builtins (cd, alias); they have no file.
    * Real use: "wrong version running" problems (which terraform, which kubectl).
* `command -v command` → Like which, but also works for builtins and aliases (use this in scripts).
* `whereis command` → Binary, source, and man page locations.
* If both a builtin and a file exist (pwd), the builtin wins.
* Bash looks in this order → alias → function → builtin → executable in $PATH.
* `echo $PATH` → Directories searched for executables, left to right.

## Getting Help

* `man command` → Full manual page.  (`/word` to search, `n` next match, `q` to quit)
* `command --help` → Short usage/help message.
* `help command` → Help for builtins only (`help cd`); fails for programs like find.
* `tldr command` → Short practical examples (fastest).
* `man -k keyword` → Search all manuals by keyword (= apropos).
* `whatis command` → One-line description.

## Command History ([ch 8](keyboard-shortcuts.md))

* `history` → Previously executed commands.
* `history | grep docker` → Find old commands containing a word.
* `↑ / ↓` → Navigate history.
* `Ctrl + R` → Reverse-search history.

## Aliases

* `alias ll='ls -la'` → Creates a shortcut (lost when the terminal closes).
* `alias` → Lists current aliases.
* `unalias ll` → Removes an alias.
* Permanent → add the line to ~/.bashrc, then `source ~/.bashrc`.
    * e.g. alias k=kubectl, alias tf=terraform
* `\ls` → Runs the real command, skipping the alias.

!!! question "Interview points"

    * `type` vs `which` → type knows aliases/builtins/functions; which only finds files in $PATH.
    * "Command not found" → check `echo $PATH`, `which cmd`, whether it's installed, and whether you need `./` for a file in the current directory.
    * "Wrong version runs" → `type -a cmd` shows every match; the first one wins.
