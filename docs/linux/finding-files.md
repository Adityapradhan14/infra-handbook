# Finding Files

*From The Linux Command Line, chapter 17*

## locate

* `locate passwd` → fast search by name from a database
* Database updated daily → misses new files → `sudo updatedb` to refresh
* `locate -i` → case-insensitive
* Use → quick "where is this file" | `find` → anything precise or recent

## find Basics

* `find [where] [tests] [action]` → e.g. `find /var/log -name "*.log" -delete`
* No path → searches current dir | `/` → whole system → add `2>/dev/null`
* Always quote wildcards → `find . -name "*.log"` → else shell expands `*` first ([ch 7](shell-expansion.md))
* Stacked tests = AND → `find /var/log -type f -name "*.log" -size +10M`

## Tests

* `-name "*.log"` → by name | `-iname` → case-insensitive
* `-type f` → file | `d` → dir | `l` → symlink
* `-size +100M` → bigger than | `-size -1k` → smaller than | units `k`, `M`, `G`
* `-mtime -1` → modified in last 1 day | `+7` → older than 7 days
* `-mmin -30` → modified in last 30 min
* `-user ganesh` | `-group devs` → by owner
* `-empty` → empty files/dirs
* `-perm 777` → exact mode → find world-writable files (security check)
* `-maxdepth 1` → don't go into subdirs

## Operators (rarely needed)

* `-o` → OR | `!` → NOT | `\( \)` → grouping
* `find . \( -name "*.log" -o -name "*.tmp" \)` → logs or tmp files
* `find . -type f ! -name "*.md"` → files that aren't markdown

## Actions

* `-print` → default, prints path
* `-delete` → delete matches → run without `-delete` first to check
* `-exec cmd {} \;` → run cmd once per file → `{}` = the file
* `-exec cmd {} +` → run cmd once with all files → faster
* `-ok cmd {} \;` → like `-exec` but asks before each
* `find . -name "*.sh" | xargs chmod +x` → same idea via xargs
* `-print0 | xargs -0` → handles spaces in filenames

## Real Use

* `find / -type f -size +500M 2>/dev/null` → what's eating disk
* `find /var/log -name "*.log" -mtime +7 -delete` → clean logs older than 7 days
* `find ~ -type f -mtime -1` → files changed today
* `find / -perm -4000 -type f 2>/dev/null` → SUID binaries (security audit)
* `find . -name "*.conf" -exec grep -l "port" {} +` → conf files containing "port"

!!! question "Interview points"

    * Disk full, find big files → `find / -type f -size +100M 2>/dev/null` or `du -sh /* | sort -h`
    * Delete logs older than 7 days → `find /var/log -name "*.log" -mtime +7 -delete`
    * `-exec {} \;` vs `{} +` → once per file vs once with all files
    * locate vs find → locate = fast but stale db, find = live search
