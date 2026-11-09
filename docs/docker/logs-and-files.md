# Logs & Files on Disk

*Hands-on notes, what Docker keeps on disk for each container*

## Where things live

| Path | What |
|---|---|
| `/usr/bin/docker` | The CLI |
| `/usr/bin/dockerd` | The daemon |
| `/var/run/docker.sock` | The API socket |
| `/etc/docker/daemon.json` | Daemon config (may not exist yet) |
| `/var/lib/docker/` | All of Docker's data |
| `/var/lib/docker/overlay2/` | Image and container layers |
| `/var/lib/docker/volumes/` | Named volumes |
| `/var/lib/docker/containers/<id>/` | One folder per container |
| `/etc/systemd/system/docker.service.d/override.conf` | Custom service override |
| `~/.docker/config.json` | Registry logins |

## A container's folder

| File | What it is |
|---|---|
| `<id>-json.log` | Everything the container printed (stdout/stderr) → `docker logs` reads this |
| `config.v2.json` | Container config: image, command, env vars, name, state |
| `hostconfig.json` | Host-side settings: `-p` mappings, restart policy, memory limits, mounts |
| `hostname` | Container's hostname (short ID by default) → mounted as `/etc/hostname` → UTS namespace |
| `hosts` | Becomes the container's `/etc/hosts` |
| `resolv.conf` | Becomes the container's `/etc/resolv.conf` → which DNS server it uses |
| `mounts/` | Extra mounts like secrets |
| `checkpoints/` | Saving container state (rare), empty |

* Container removed (`docker rm` / `--rm`) → whole folder deleted, logs included

## The `-json.log` file

* One JSON object per line → `{"log": "text", "stream": "stdout or stderr", "time": "..."}`
* App writes output → shim catches it → `dockerd` saves it here (`json-file` log driver)
* `stream` → where it came from → nginx entrypoint wrote to stdout, nginx `[notice]` lines go to stderr by design
* `time` ends in `Z` → UTC → 13:15 in the log = 18:45 IST
* `cat <id>-json.log | jq` → pretty-prints each JSON object

## `docker logs`

* `docker logs app1` → nice reader for that file, strips the JSON, shows only the text
* `docker logs -f app1` → follow live, Ctrl+C stops watching, container keeps running
* `docker logs -t app1` → with timestamps from the `time` field
* `docker inspect -f '{{.LogPath}}' app1` → exact path of the log file

## Log growth

* Log file grows forever by default → chatty container can fill the disk
* Cap it in `/etc/docker/daemon.json` → `"log-driver": "json-file"`, `"log-opts": {"max-size": "10m", "max-file": "3"}` → max 3 files of 10 MB per container (not applied yet)

## Lab: reading a container's files

```bash
sudo ls /var/lib/docker/containers/<id>
sudo cat /var/lib/docker/containers/<id>/<id>-json.log | jq
```

| Symptom | Cause | Fix |
|---|---|---|
| `cat: ...: Is a directory` + `No such file or directory` | Space instead of `/` between folder and file → `cat` got two arguments | Join with `/` → `<folder>/<file>` |
| `cd 56: No such file or directory` | Linux needs the full name, doesn't guess | Type `cd 56` + Tab → bash completes it |

* `sudo su -` → full root shell, mistakes get costly → prefer `sudo ls` / `sudo cat` for one-off reads

!!! question "Interview points"

    * Where does docker logs get its data? → from /var/lib/docker/containers/<id>/<id>-json.log, written by the json-file log driver
    * How do you find a container's log file path? → docker inspect -f '{{.LogPath}}' <name>
    * Why do nginx notices appear as stderr? → nginx writes its own logs to stderr by design; it does not mean an error
    * What happens to logs when a container is removed? → the whole container folder, logs included, is deleted
    * How do you stop container logs filling the disk? → set log-opts max-size and max-file in /etc/docker/daemon.json
    * Where does a container's /etc/hostname, /etc/hosts and /etc/resolv.conf come from? → files in its folder under /var/lib/docker/containers, mounted in at start
