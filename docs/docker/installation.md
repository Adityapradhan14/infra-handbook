# Install & Upgrade

*Hands-on notes, upgrading Docker on Ubuntu 24.04*

## Find how Docker was installed

```bash
docker --version
dpkg -l | grep -E 'docker|containerd' | awk '{print $2, $3}'
snap list 2>/dev/null | grep docker
```

* `docker-ce` → Docker's official apt repo → upgrade with apt
* `docker.io` → Ubuntu's own package, usually behind → remove it, switch to the official repo
* Shows in `snap list` → snap install → `sudo snap refresh docker`, has sandbox quirks with paths/permissions
* Mine → `docker-ce 5:29.9.2` + `containerd.io`, `docker-buildx-plugin`, `docker-compose-plugin`, `docker-ce-rootless-extras`, Ubuntu 24.04 (noble)

## Upgrade (official repo)

```bash
sudo apt update
apt list --upgradable 2>/dev/null | grep -E 'docker|containerd'
sudo apt install --only-upgrade docker-ce docker-ce-cli docker-ce-rootless-extras containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl restart docker
docker version
docker compose version
```

* `apt list --upgradable` empty → already on the latest version in the repo
* Restart → running containers stop → `restart: always` / `unless-stopped` come back on their own
* Specific version → `apt-cache madison docker-ce` then `sudo apt install docker-ce=<VERSION> docker-ce-cli=<VERSION>`

## Switching from `docker.io`

* `sudo apt remove docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc` → removes packages, keeps data in `/var/lib/docker` (no `--purge`)
* Then add Docker's GPG key + apt repo → install `docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin`
* Removing snap Docker → DOES delete its images and volumes
* Compose v2 → `docker compose` (space, plugin) | old `docker-compose` (hyphen) → deprecated
* Run docker without sudo → `sudo usermod -aG docker $USER`, log out and in → `docker` group = root-equivalent

## systemd and socket activation

* `systemctl status docker` → `Loaded: ...; disabled` + `TriggeredBy: docker.socket`
* disabled → `dockerd` does not start at boot
* Socket activation → systemd listens on `docker.socket`, starts `dockerd` only when something connects to it
* `sudo systemctl enable --now docker` → start at boot + start now
* Drop-in → `/etc/systemd/system/docker.service.d/override.conf` → local customisation of the service (mine adds `--exec-opt native.cgroupdriver=systemd`)

## Lab: `docker0` missing

| Symptom | Cause | Fix |
|---|---|---|
| `ifconfig` showed no `docker0` | `dockerd` wasn't running: service disabled, only socket-activated, nothing had touched the socket yet | `sudo systemctl enable --now docker` |
| `docker --version` worked anyway | Only the CLI runs for that, it never talks to the daemon | `docker version` shows both client and server |
| `docker0` shows `state DOWN`, `NO-CARRIER` | Normal: no containers plugged into the bridge | Run a container → it goes UP |

* `ifconfig` → deprecated, hides down interfaces → use `ip a` / `ip -br a`
* `docker0` only exists while `dockerd` runs → `dockerd` creates it at startup → see [Networking](networking.md)

!!! question "Interview points"

    * How do you check how Docker was installed on Ubuntu? → dpkg -l for docker-ce vs docker.io, and snap list
    * docker.io vs docker-ce? → docker.io is Ubuntu's package and lags behind; docker-ce comes from Docker's official repo
    * Service shows disabled but Docker works? → socket activation: systemd starts dockerd when something connects to docker.socket
    * Why is docker0 missing? → dockerd isn't running (or bridge is disabled in daemon.json); dockerd creates docker0 at startup
    * enable vs start? → start runs it now, enable starts it at boot; enable --now does both
    * Does removing docker.io delete my images? → no, apt remove without --purge keeps /var/lib/docker
