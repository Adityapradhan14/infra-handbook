# Permissions

*From The Linux Command Line, chapter 9*

* Permissions → control who can read, write or execute a file or directory.
* 3 classes → `u` owner | `g` group | `o` others | `a` all
* 3 permissions → `r` = 4 | `w` = 2 | `x` = 1

## Identity

* `id` → your UID, GID and groups. `id ganesh`
* `groups` → groups you belong to
* `whoami` → current username
* `/etc/passwd` → user accounts (no passwords) | `/etc/shadow` → hashed passwords (root only) | `/etc/group` → groups
* New group membership applies after logout/login (or `newgrp group`).

## Reading `ls -l`

* `-rwxr-xr-- 1 ganesh devs 220 Oct 28 script.sh`
* type | owner | group | others | links | owner | group | size | date | name
* Type → `-` file | `d` directory | `l` symlink | `c`/`b` character/block device | `s` socket | `p` pipe

## Files vs Directories

* File → `r` read contents | `w` change contents | `x` run it
* Dir → `r` list names | `w` create/delete/rename entries | `x` enter (`cd`) and access files inside
* Dir `r` without `x` → can see names but not open anything.
* Dir `w` needs `x` too to actually create or delete.
* Deleting a file needs `w` on the DIRECTORY, not the file. You can delete a read-only file in your own folder.

## Octal

* `7` rwx | `6` rw- | `5` r-x | `4` r-- | `3` -wx | `2` -w- | `1` --x | `0` ---
* `755` → rwxr-xr-x → scripts, directories
* `644` → rw-r--r-- → normal files
* `700` → rwx------ → private directory
* `600` → rw------- → secrets, SSH private keys, `.env` files
* `777` → everyone can write. Almost never correct.

## chmod

* `chmod 755 f` → octal
* `chmod u+x f` | `chmod g-w f` | `chmod o=r f` | `chmod a+x f` → symbolic (`+` add, `-` remove, `=` set exactly)
* `chmod u=rwx,go=rx f` → several classes at once
* `chmod -R 755 dir` → recursive (careful: makes every file executable)
* `stat f` → shows permissions in both forms (e.g. 0644/-rw-r--r--)

## chown / chgrp

* `sudo chown aditya f` → change owner
* `sudo chown aditya:devs f` → owner and group | `sudo chown :devs f` → group only
* `sudo chgrp devs f` → group only
* `-R` → recursive
* Only root can change a file's owner.

## umask

* Sets the default permissions for new files and directories.
* Base → file `666` | dir `777` (new files never get `x` by default)
* `umask 022` → files `644`, dirs `755` (Ubuntu default)
* `umask 077` → files `600`, dirs `700` (private)
* It's a mask that REMOVES bits, not subtraction: `umask 033` → files `644` (not 633)
* `umask` alone shows the current value; set it in ~/.bashrc to make it permanent.

## Special Bits

* setuid → `4000`, `chmod u+s f` → program runs as the FILE'S OWNER. `/usr/bin/passwd` (`-rwsr-xr-x`) runs as root so you can edit /etc/shadow.
* setgid → `2000`, `chmod g+s` → on a program: runs as the file's group. On a DIRECTORY: new files inherit the directory's group (shared team folders).
* sticky → `1000`, `chmod +t dir` → in that directory, only a file's owner (or root) can delete it. `/tmp` → `drwxrwxrwt`
* `chmod 2770 /srv/shared` → setgid + rwxrwx---
* Lowercase `s`/`t` → bit set AND x set | uppercase `S`/`T` → bit set but x missing (usually a mistake)
* setuid is ignored on shell scripts (security).
* `find / -perm -4000 2>/dev/null` → list all setuid files (security audit)

## sudo / su

* `sudo cmd` → run one command as root; asks for YOUR password.
* `sudo -l` → what you're allowed to run | `sudo -i` → root shell
* `sudo -u alice cmd` → run as another user
* Rules live in `/etc/sudoers`; edit only with `sudo visudo` (checks syntax, so you can't lock yourself out)
* `su user` → switch user; asks for THAT user's password
* `su - user` → full login shell (their env and home) | `su -` → root
* `passwd` → change your password | `sudo passwd alice` → set someone else's

!!! tip "Quick revision"

    * `r=4 w=2 x=1` | `u g o a`
    * `755` scripts/dirs | `644` files | `600` secrets | `777` never
    * `chmod` permissions | `chown` owner | `chgrp` group | `umask` defaults
    * setuid `4` runs as owner | setgid `2` inherits group | sticky `1` only owner deletes
    * `sudo` your password | `su` their password

!!! question "Interview points"

    * "Permission denied running ./script.sh" → check `x` bit (`ls -l`), `chmod +x`; run `bash script.sh` to bypass; check if the disk is mounted `noexec`.
    * Even root can't run a file with no `x` bit at all; root can read/write anything.
    * SSH says "permissions are too open" → `chmod 600 ~/.ssh/id_ed25519`, `chmod 700 ~/.ssh`.
    * Deleting a file is controlled by the directory's `w`, not the file's.
    * Directory `x` = permission to enter/access; `r` = permission to list names.
    * `/tmp` is 1777: everyone writes, sticky bit stops users deleting each other's files.
