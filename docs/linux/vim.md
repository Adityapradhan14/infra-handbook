# vi / vim

*From The Linux Command Line, chapter 12*

## Why

* Always installed on servers → nano may not be → must be able to edit a config and exit
* vi = original | vim = improved vi → on Ubuntu, `vi` opens vim

## Modes

* Normal (command) mode → default on open → keys are commands, not text
* Insert mode → `i` → type text → `Esc` → back to normal
* Command-line mode → `:` from normal → `:w`, `:q` etc.
* Lost? → press `Esc` twice → you're in normal mode

## Open + Save + Quit

* `vim file.txt` → open/create
* `:w` → save | `:q` → quit | `:wq` or `:x` or `ZZ` → save + quit
* `:q!` → quit without saving (discard changes)
* `:w newname` → save as

## Enter Insert Mode

* `i` → insert before cursor | `a` → after cursor
* `I` → start of line | `A` → end of line
* `o` → new line below | `O` → new line above

## Move (normal mode)

* `h` `j` `k` `l` → left down up right (arrow keys also work)
* `w` → next word | `b` → back a word
* `0` → start of line | `$` → end of line
* `gg` → first line | `G` → last line | `25G` or `:25` → go to line 25

## Edit (normal mode)

* `x` → delete char | `dd` → delete (cut) line | `3dd` → 3 lines
* `dw` → delete word | `D` → delete to end of line
* `yy` → copy (yank) line | `p` → paste below | `P` → paste above
* `u` → undo | `Ctrl-r` → redo
* `.` → repeat last change

## Search + Replace

* `/word` → search forward | `n` → next | `N` → previous
* `:%s/old/new/g` → replace all in file
* `:%s/old/new/gc` → replace all, confirm each

## Useful

* `:set number` → line numbers | `:set nonumber` → off
* `vim +25 file` → open at line 25 (from error messages)
* `sudo vim /etc/ssh/sshd_config` → edit system files as root
* `E45: 'readonly' option is set` → opened without sudo → `:q!` and reopen with sudo

!!! question "Interview points"

    * How to exit vim without saving → `Esc` then `:q!`
    * Edit a config on a server with no nano → `vim`, `i`, edit, `Esc`, `:wq`
