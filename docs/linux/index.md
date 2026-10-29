---
hide:
  - toc
---

# Linux

*Based on The Linux Command Line by William Shotts. The notes are my own.*

Shell and system fundamentals for day-to-day ops work. The chapters are in reading order, and each one links to the next.

<div class="ih-chapters" markdown>

1. [The Shell](shell-basics.md)
    Shell vs terminal, the prompt, first commands
2. [Navigation](navigation.md)
    The filesystem tree, `cd`, absolute and relative paths
3. [Exploring the System](exploring-the-system.md)
    `ls`, reading files, key directories, symlinks
4. [Files & Directories](files-and-directories.md)
    Wildcards, `cp`, `mv`, `rm`, hard and soft links
5. [Working with Commands](working-with-commands.md)
    `type`, `which`, getting help, aliases
6. [Redirection & Pipes](redirection.md)
    Streams, `2>&1`, `tee`, filters
7. [Expansion & Quoting](shell-expansion.md)
    Globbing, braces, `$(...)`, quoting rules
8. [Keyboard Shortcuts](keyboard-shortcuts.md)
    Line editing, history, job control keys
9. [Permissions](permissions.md)
    `chmod`, `chown`, `umask`, special bits, `sudo`
10. [Processes](processes.md)
    `ps`, `top`, process states, signals, jobs
11. [systemd & Services](systemd.md)
    `systemctl`, unit files, start vs enable, `journalctl`
12. [vi / vim](vim.md)
    Modes, editing, search and replace
13. [Package Management](package-management.md)
    `apt`, `dpkg`, packages in Dockerfiles
14. [Networking](networking.md)
    IPs, routes, ports, DNS, `curl`, SSH
15. [Finding Files](finding-files.md)
    `locate`, `find` tests and actions

</div>
