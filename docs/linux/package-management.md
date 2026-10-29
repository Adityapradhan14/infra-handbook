# Package Management

*From The Linux Command Line, chapter 14*

## Basics

* Package → archive with program files + metadata (version, deps, scripts) → Debian/Ubuntu use `.deb`
* Repository → server hosting packages → listed in `/etc/apt/sources.list.d/`
* Dependency → package needs another to work → apt resolves automatically
* Two levels → `apt` (high: repos + deps) | `dpkg` (low: local `.deb`, no dep resolution)

## Find + Inspect

* `apt update` → refresh package index only, installs nothing
* `apt search nginx` → search repos by name/desc
* `apt show nginx` → version, deps, size before install
* `apt list --installed | wc -l` → count installed pkgs
* `apt list --upgradable` → what has updates
* `apt-cache depends htop` → what htop needs
* `apt-cache rdepends --installed libc6` → what needs libc6

## Install + Remove

* `sudo apt install -y htop` → install from repo (`-y` = no prompt)
* `sudo dpkg -i file.deb` → install local `.deb` → then `sudo apt -f install` to fix missing deps
* `sudo apt upgrade` → install newer versions of installed pkgs
* `sudo apt remove htop` → remove binary, keep config files
* `sudo apt purge htop` → remove binary + config
* `sudo apt autoremove` → delete deps no longer needed

## Query dpkg

* `dpkg -l | grep htop` → is it installed (`ii` = installed, `rc` = removed but config left)
* `dpkg -L htop` → list every file the pkg installed
* `dpkg -S $(which ls)` → which pkg owns a file → e.g. `coreutils: /usr/bin/ls`

## Docker / Scripts

* `apt-get` (not `apt`) in scripts/Dockerfiles → stable output for scripts
* One layer, smaller image:

```dockerfile
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
```

!!! question "Interview points"

    * update vs upgrade → update = refresh list, upgrade = install new versions
    * remove vs purge → purge also deletes config
    * "Unable to locate package" → run `apt update`, check spelling, check repo enabled
    * "Which package gave me this file?" → `dpkg -S /path`
