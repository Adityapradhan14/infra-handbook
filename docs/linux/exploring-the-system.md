# Exploring the System

*From The Linux Command Line, chapter 3*

## ls options

* `ls` → Lists files and directories.
* `ls -l` → Long listing: permissions, links, owner, group, size, modification time.
* `ls -a` → All files, including hidden ones (`.` prefix).
* `ls -la` → Long listing + hidden files.
* `ls -h` → Human-readable sizes (K, M, G); use with -l → `ls -lh`.
* `ls -t` → Sort by modification time (newest first).
* `ls -r` → Reverse the sort order.
* `ls -S` → Sort by size.
* `ls -ld dir` → Info about the directory itself, not its contents.
* Options combine: `ls -lth` → long, newest first, readable sizes.

## Reading a long listing

```
-rw-r--r-- 1 root root 3576 Apr 1 10:00 file.txt
```

* `-` → file type (`-` file, `d` directory, `l` symlink)
* `rw-r--r--` → permissions: owner / group / others
* `1` → number of hard links
* `root root` → owner, group
* `3576` → size in bytes
* `Apr 1 10:00` → last modified
* `file.txt` → name

## Viewing File Content

* `cat file` → Displays the complete contents of a file.
* `less file` → Views a file page by page; good for large files.
    * `/word` search, `n` next match, `G` end, `g` start, `q` quit
* `head file` → First 10 lines by default (`head -n 20 file` for 20).
* `tail file` → Last 10 lines by default; `tail -f file` follows a live log.

## File Information

* `file filename` → Determines the file type (Linux ignores extensions).
* `wc file` → Counts lines, words, and bytes (`wc -l` lines only).
* `du -sh dir` → Disk usage of a directory, human-readable.
* `df -h` → Free/used space per filesystem, human-readable.

## Key directories

* `/` → root of everything
* `/etc` → system config files
* `/var/log` → logs
* `/home` → users' home dirs; `/root` → root's home
* `/bin`, `/usr/bin` → programs; `/sbin` → admin programs
* `/tmp` → temp files, cleared on reboot
* `/proc` → live kernel/process info (virtual, not on disk)
* `/dev` → device files
* `/opt` → third-party software
* `/boot` → kernel + bootloader

## Symbolic links (symlinks)

* A symlink = a shortcut / a note that points to another file or folder.
* It holds no content, only the path to the target.
* `ls -l` shows it as `l` at the start and `link -> target`.
* Delete the target → the link breaks ("No such file or directory").

## Creating and replacing links

* `ln -s target link` → create a new symlink
* `ln -sf target link` → replace an existing link to a file (-f = force)
* `ln -sfn target link` → replace an existing link to a folder
    * (-n = treat the link itself, don't follow it into the folder)
* `-sfn` is safe for files too, so it can be used for every replacement.

## Real examples on Ubuntu

* `/etc/localtime -> /usr/share/zoneinfo/Asia/Kolkata` → timezone
* `/usr/bin/python3 -> python3.12` → version switch
* `/bin -> usr/bin` → whole folder is a link

## DevOps use: deploys and rollbacks

* `/app/current -> /app/releases/v2`; the server always runs from /app/current
* Deploy: `ln -sfn /app/releases/v3 /app/current`
* Rollback: `ln -sfn /app/releases/v2 /app/current` (instant)
