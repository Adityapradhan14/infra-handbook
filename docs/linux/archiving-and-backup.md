# Archiving & Backup

*From The Linux Command Line, chapter 18*

## Core idea

* Archive → bundle many files into one, keeps perms/owners/timestamps → `tar`
* Compress → shrink one file → `gzip`, `bzip2`, `xz`
* `.tar.gz` → archive then compress → standard on Linux
* `zip` → does both but loses Unix perms/ownership → avoid for Linux backups
* Use cases → backups, deploys, moving data between servers

## tar

* Flags → `c` create | `x` extract | `t` list | `f` filename next | `z` gzip | `v` verbose | `C` extract into dir
* `tar -czf backup.tar.gz dir/` → create
* `tar -tzf backup.tar.gz` → list without extracting
* `tar -xzf backup.tar.gz -C /tmp/` → extract into `/tmp`
* `tar rf a.tar file` → append → only plain `.tar`, not `.tar.gz`
* `bzip2` / `xz` → smaller, slower → `tar j` = bzip2, `tar J` = xz
* Leading `/` stripped on create → paths inside archive start `home/me/...` → check with `tar tf`
* `tar xf a.tar --wildcards 'home/me/dir-*/file-A'` → extract only matching paths → quote so shell doesn't expand `*`
* `find dir -name 'file-A' -exec tar rf a.tar '{}' '+'` → add found files → `+` runs tar once, `\;` once per file (see [Finding Files](finding-files.md))

## gzip

* `gzip file` → `file.gz`, original deleted → `gzip -k` keeps it
* `gunzip file.gz` → back → `zcat` / `zless` to view without extracting
* `gzip -l file.gz` → compressed vs original size
* Works on single files only → `gzip dir/` fails

## rsync

* Syncs src → dest, copies only new/changed files → compares size + mtime
* Over network sends only changed blocks → fast reruns, resumes broken transfers
* `rsync -av src/ dest/` → `a` = recursive + keep perms/times, `v` = verbose
* `rsync -avn` → dry run
* `rsync -av --delete` → exact mirror, removes extras in dest
* `rsync -av src/ user@host:/backup/` → over SSH
* `src/` → copies contents | `src` → copies the folder itself

!!! tip "Quick revision"

    * `tar -czf` create | `tar -tzf` list | `tar -xzf ... -C dir` extract
    * `rsync -avn` first, then run for real → add `--delete` only for an exact mirror

!!! question "Interview points"

    * Archive vs compress → `tar` bundles, `gzip` shrinks, `zip` loses Unix metadata
    * `rsync` vs `scp` → `scp` copies everything every time, `rsync` only changes + resumes
    * `rsync src/` vs `rsync src` → trailing slash copies contents, no slash copies the folder itself
