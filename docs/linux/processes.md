# Processes

*From The Linux Command Line, chapter 10*

* Process → a running instance of a program. `vim file.txt` → vim becomes a process.
* PID → unique process ID | PPID → parent's PID
* PID 1 → `systemd` on Ubuntu; starts and manages services; adopts orphaned processes.
* `/proc/<PID>/` → kernel's live info about each process (`cat /proc/1234/status`)

## Viewing Processes

* `ps` → processes in the current shell
* `ps x` → all your processes, including ones with no terminal
* `ps aux` → all processes, all users (BSD style)
* `ps -ef` → same, but shows PPID (System V style)
* `ps aux --sort=-%mem | head` → top memory users | `--sort=-%cpu` → top CPU users
* Columns to read → USER, PID, %CPU, %MEM, STAT, COMMAND
* `ps aux | grep nginx` → also shows the grep itself; `pgrep -a nginx` is cleaner.
* `pstree` → parent/child tree | `pstree -p` → with PIDs

## top / htop

* `top` → live view of processes, CPU, memory, load. `q` quits.
* Inside top → `M` sort by memory | `P` sort by CPU | `k` kill a PID | `1` show each CPU
* Load average → 3 numbers = 1, 5, 15 min. Compare with CPU count (`nproc`): load 4 on 4 CPUs = fully busy.
* `htop` → friendlier, colour, scrolling. `sudo apt install htop`

## Process States (STAT column)

* `R` → running | `S` → sleeping (waiting for something) | `T` → stopped (Ctrl-Z)
* `D` → uninterruptible sleep, usually waiting on disk/network; even `kill -9` can't stop it.
* `Z` → zombie: finished, but the parent hasn't collected its exit status.
* Can't kill a zombie (it's already dead) → fix or restart its parent; once the parent dies, PID 1 cleans it up.
* Orphan → parent died while the child is still running; PID 1 adopts it.

## Foreground / Background

* `cmd &` → run in the background. `sleep 100 &` → prints `[1] 4321` (job number, PID)
* `Ctrl-Z` → pause the foreground job
* `bg` / `bg %1` → resume it in the background
* `fg` / `fg %1` → bring it to the foreground
* `jobs` → list jobs in this shell (`jobs -l` adds PIDs)
* Background jobs die when the terminal closes (SIGHUP).
* `nohup cmd &` → keeps running after logout (output → nohup.out) | `disown` → detach an already-running job

## Signals

* `kill` sends a SIGNAL; it doesn't always mean "kill".
* `kill PID` → SIGTERM (15): polite request; program can clean up and save.
* `kill -9 PID` → SIGKILL (9): kernel removes it instantly; can't be caught or ignored; no cleanup.
* `kill -1 PID` → SIGHUP: many daemons (nginx) reload their config on it.
* `Ctrl-C` → SIGINT (2) | `Ctrl-Z` → SIGTSTP (pause)
* `kill -STOP PID` / `kill -CONT PID` → pause / resume any process
* `kill -l` → list all signals
* Right order → `kill PID`, wait a few seconds, then `kill -9` only if it's still alive.

## Kill by Name

* `pgrep nginx` → PIDs by name | `pgrep -a` → with full command | `pgrep -u ganesh` → by user
* `pkill nginx` → signal all matching processes (careful: matches partial names)
* `killall nginx` → same, exact name match

## Which process holds a port

* `sudo ss -tlnp` → listening ports with the process using each
* `sudo lsof -i :80` → what's using port 80

!!! tip "Quick revision"

    * `ps aux` / `ps -ef` snapshot | `top` live | `pgrep` find | `pstree` tree
    * `&` background | `Ctrl-Z` pause | `bg` / `fg` resume | `jobs` list | `nohup` survive logout
    * `kill` TERM 15 | `kill -9` KILL | `kill -1` HUP reload | `Ctrl-C` INT 2
    * `R` run | `S` sleep | `D` disk wait | `T` stopped | `Z` zombie

!!! question "Interview points"

    * SIGTERM vs SIGKILL → TERM lets the program clean up (close files, release locks, finish writes); KILL can't be caught, so data or locks can be left broken. Always TERM first.
    * Zombie → finished process whose parent hasn't read its exit status. `kill -9` does nothing; deal with the parent.
    * `D` state process won't die even with `kill -9` → it's stuck on I/O (often a disk or NFS issue).
    * "Server is slow" → `top` (load average, CPU vs `nproc`, memory, swap) → sort by `P`/`M` → `ps aux --sort=-%cpu | head` → check that process's logs.
    * "Port 8080 already in use" → `sudo ss -tlnp | grep 8080` → find the PID → `kill` it or stop its service.
    * PID 1 is systemd; it starts services and adopts orphans.
