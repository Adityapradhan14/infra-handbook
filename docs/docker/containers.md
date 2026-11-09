# Containers

*Hands-on notes, running and cleaning up containers*

## Processes and signals

* Process → a running program, has a PID | PID 1 on the host → `systemd`
* A container is just a process → main process exits = container stops
* Signals → `SIGTERM` (15) "shut down cleanly" | `SIGKILL` (9) "die now", can't be ignored | `SIGINT` (2) → what Ctrl+C sends
* `docker stop` → SIGTERM, waits 10s, then SIGKILL | `docker kill` → SIGKILL immediately
* nginx image sets its stop signal to `SIGQUIT` → finish current requests, then quit → `Exited (0)`

## Lifecycle

* created → running → paused → running → stopped (exited) → removed

| State | Meaning |
|---|---|
| Created | Set up, process not started |
| Running | Main process alive |
| Paused | Process frozen (cgroup freezer) |
| Exited | Main process ended, container still exists with its writable layer |
| Removed | Gone completely |

* Stopped container is NOT deleted → sits there until `docker rm`
* `docker run ubuntu` exits instantly → default command `bash`, no terminal attached → bash exits
* Exit codes → `0` success | `1` app error | `137` SIGKILL / out of memory | `143` SIGTERM
* Restart policies → `no` (default) | `on-failure` | `always` | `unless-stopped`

## Foreground vs detached

* No `-d` → attached to terminal, shows the app's output, looks "stuck" → nginx is a server, meant to run forever
* `-d` → runs in background, prints the container ID, terminal comes back
* `-it` → `-i` keep input open + `-t` give it a terminal → for interactive shells

## `docker run` flags

| Flag | Meaning |
|---|---|
| `-d` | Detached (background) |
| `-it` | Interactive + terminal |
| `--name x` | Own name instead of a random one |
| `--rm` | Delete automatically when it stops |
| `-p H:C` | Publish container port C on host port H |
| `-v src:dst` | Volume or bind mount |
| `-e KEY=val` | Environment variable |
| `--network n` | Join a network |
| `--restart` | Restart policy |
| `-m` / `--cpus` | Memory / CPU limits (cgroups) |

* Flags go AFTER the subcommand → `docker run --rm ...` ✓ | `docker --rm ...` ✗ `unknown flag`
* No `--name` → random adjective_scientist name (`wizardly_boyd`, `stoic_wu`)
* `--rm` → container + writable layer deleted as soon as it stops → `docker stop` alone leaves nothing in `ps -a`
* `--rm` does NOT let `docker rm` delete a running container → only cleans up after stop
* `--rm` for throwaway/test containers → skip it when I need the logs or exit code afterwards

## Command shapes

* `docker <object> <action>` → `container`, `image`, `volume`, `network`, `system`
* Old shortcuts → `docker ps` = `docker container ls` | `docker run` = `docker container run` | `docker rmi` = `docker image rm`
* `run` → creates a NEW container | `start` → restarts an existing stopped one → running `run` again = second container
* `run` → new container | `exec` → command inside an existing running one → `docker exec -it web bash`

## Listing and cleaning up

* `docker ps` → running only | `docker ps -a` → all, including stopped
* `-q` → IDs only, no table → `docker ps -aq` = IDs of all containers
* `$( ... )` → runs the inner command and pastes its output in place
* `docker rm $(docker ps -aq)` → remove every stopped container (running ones error out)
* `docker rm -f $(docker ps -aq)` → force-remove everything, running too → careful
* `docker stop $(docker ps -q)` → stop all running, don't delete
* `--filter ancestor=nginx` → only containers made from that image
* `docker container prune` → remove stopped containers only
* `docker stop` + `docker rm` → clean | `docker rm -f` → SIGKILL + remove in one step, fine for tests, not for databases
* `docker rm` removes containers | `docker rmi` removes images → image stays after `rm`, next run starts instantly

## Bash: multi-line commands

* Unfinished line + Enter → bash doesn't run it, shows `>` (continuation prompt `PS2`) and waits
* `for i in {1..10}; do` → Enter → `docker run -d nginx:latest` → Enter → `done` → Enter → runs 10 containers
* One line → `for i in {1..10}; do docker run -d nginx:latest; done` → `;` replaces line breaks
* Bash keeps waiting after → `for/while ... do` (needs `done`) | `if ... then` (needs `fi`) | line ending in `\` | unclosed quote | line ending in a pipe or `&&`
* Long docker commands → split with `\` at the end of each line
* Stuck at `>` → Ctrl+C

## Debugging toolkit

* `docker ps -a` → all containers | `docker logs -f x` → output live | `docker inspect x` → everything as JSON
* `docker exec -it x sh` → get inside | `docker stats` → live CPU/RAM | `docker system df` → disk used

## Lab: first containers

```bash
docker run --name app1 nginx:latest
docker run --rm -d --name app1 nginx
for i in {1..10}; do docker run -d nginx:latest; done
docker ps -a
docker rm $(docker ps -aq)
```

| Symptom | Cause | Fix |
|---|---|---|
| Terminal stuck on nginx log lines | Ran in foreground (no `-d`), nginx runs forever | Ctrl+C, then use `-d` |
| `cannot remove container "app1": container is running` | `docker rm` refuses running containers | `docker stop app1` then `docker rm app1`, or `docker rm -f app1` |
| `unknown flag: --rm` | Left out `run`, flags belong to the subcommand | `docker run --rm -d --name app1 nginx` |
| 10 containers `Exited (0)` still listed | Stopped containers aren't deleted | `docker rm $(docker ps -aq)` |
| `ps -a` empty after `docker stop` | Started with `--rm` | Expected |
| `docker exect`: `unknown shorthand flag: 'i'` | Typo, `exect` isn't a command | `docker exec` |
| `'docker exec' requires at least 2 arguments` | Gave the command but no container | `docker exec -it app1 bash` → container + command |

!!! question "Interview points"

    * Why does a container exit immediately? → its main process ended; e.g. bash with no terminal exits at once
    * docker stop vs docker kill? → stop sends SIGTERM, waits 10s, then SIGKILL; kill sends SIGKILL immediately
    * Is a stopped container deleted? → no, it stays with its writable layer until docker rm
    * What does --rm do? → deletes the container automatically when it stops; it does not remove a running container
    * docker run vs docker start? → run creates a new container; start restarts an existing stopped one
    * docker run vs docker exec? → run makes a new container; exec runs a command inside an existing running one
    * docker ps -aq? → IDs of all containers, running and stopped, used with $( ) to feed other commands
    * docker rm vs docker rmi? → rm removes containers, rmi removes images
    * Exit code 143? → the process got SIGTERM
