# The Shell

*From The Linux Command Line, chapter 1*

* Shell → a command-line interpreter that sits between the user and the Linux OS.
* It interprets commands, executes programs, and manages redirection, pipes, variables and scripting.
* The shell asks the kernel (through system calls) to start programs; the programs do the actual work.
* Terminal → application/interface used to access a shell.
* Terminal emulator → GUI app that gives you a terminal (gnome-terminal, Konsole).

## Shell ≠ Terminal

* Terminal → provides the interface
* Shell → interprets and executes commands

## Common shells

* Bash → Bourne Again Shell (Ubuntu default)
* Zsh
* Fish
* sh

## Prompt

* `user@host:dir$` → standard bash prompt
* `$` → normal user | `#` → root

## Basics

* `↑` / `↓` → command history (bash keeps ~1000 by default)
* `date` → current date/time
* `cal` → calendar
* `df -h` → disk free space
* `free -h` → memory usage
* `exit` or `Ctrl-D` → ends the session
