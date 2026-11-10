# Volumes & Bind Mounts

*Hands-on notes, Docker storage*

## Why containers need them

* Container filesystem → a writable layer that lives and dies with the container, `docker rm` deletes it
* Two problems → data is lost when the container goes, and the container cannot see host files
* Fix → mount something into the container: a volume, a bind mount, or `tmpfs`

## The three mount types

* Volume → storage created and managed by Docker, referred to by name → `pgdata`
* Bind mount → a host path you choose, mapped into the container, same real files on both sides → `/home/ganesh/site`
* `tmpfs` → memory only, never written to disk, gone when the container stops (Linux only) → `--tmpfs /tmp`

## -v versus --mount

* `-v SOURCE:TARGET` → short form, Docker guesses the type from `SOURCE`
* Source starts with `/` or `./` → bind mount | just a name → named volume
* `--mount type=...,source=...,target=...` → long form, explicit, no guessing
* `-v` with a wrong host path → silently creates an empty root-owned directory
* `--mount type=bind` with a wrong host path → fails with an error, which is what you want

```bash
# named volume
docker run -v pgdata:/var/lib/postgresql/data postgres
docker run --mount type=volume,source=pgdata,target=/var/lib/postgresql/data postgres

# bind mount
docker run -v /home/ganesh/site:/usr/share/nginx/html nginx
docker run --mount type=bind,source=/home/ganesh/site,target=/usr/share/nginx/html nginx
```

## When to use which

* Volume → data the app owns and must keep: databases, uploads
* Bind mount → files you edit or inspect from the host: source code in development, a single config file
* Bind mount → host resources only a path can reach: logs, `/proc`, [the Docker socket](docker-socket.md)
* Avoid bind mounts for production data → they tie the container to one host's folder layout and let the container change host files
* Read-only mount → add `:ro` (`-v /home/ganesh/site:/usr/share/nginx/html:ro`) when the container only needs to read
* Mount the narrowest path possible → one file or subfolder, not a parent directory

## Volume commands

* `docker volume create pgdata` → create a named volume (also auto-created on first use)
* `docker volume ls` → list volumes
* `docker volume inspect pgdata` → shows `Mountpoint`, the real path on the host
* `docker volume rm pgdata` → delete it, fails if a container still uses it
* `docker volume prune` → delete every volume no container uses, check first, this is permanent
* `docker system df` → disk used by images, containers and volumes

## Where volumes live on the host

* Path → `/var/lib/docker/volumes/<name>/_data`, the contents are in `_data`
* Owned by root → `cd /var/lib/docker/volumes` as a normal user gives `Permission denied`, use `sudo`
* Docker Desktop (Mac/Windows) → the path is inside a hidden VM, not browsable
* Don't edit files there while a container is using the volume
* Change the base location → `data-root` in `/etc/docker/daemon.json`, but that moves all Docker data

## Back up and restore a volume

* Idea → throwaway container mounts the volume and a host folder, then runs `tar`
* This uses a named volume and a bind mount together

```bash
# backup
docker run --rm -v mongodb:/data -v "$PWD":/backup alpine \
  tar czf /backup/mongodb.tar.gz -C /data .

# restore into a volume
docker run --rm -v mongodb:/data -v "$PWD":/backup alpine \
  tar xzf /backup/mongodb.tar.gz -C /data
```

## Lab: Mongo with and without a volume

* No volume → data lives in the container's writable layer
* `--rm` → removes the container on stop
* Named volume → survives `--rm`, only `docker volume rm` deletes it
* Mongo keeps its data in `/data/db`

```bash
# 1. no volume
docker run --rm -d --name mongodb -p 27017:27017 mongo:latest
docker exec -it mongodb mongosh
#    test> db.helo.insertMany([...])   → show dbs lists "test"
docker stop mongodb
docker run --rm -d --name mongodb -p 27017:27017 mongo:latest
#    show dbs → "test" is gone, the data went with the container

# 2. with a named volume
docker volume create mongodb
docker run --rm -d --name mongodb -v mongodb:/data/db -p 27017:27017 mongo:latest
#    insert the same documents, then:
docker stop mongodb
docker run --rm -d --name mongodb -v mongodb:/data/db -p 27017:27017 mongo:latest
#    db.helo.find() → all documents are back

# 3. look at the files on the host
sudo ls /var/lib/docker/volumes/mongodb/_data
#    collection-*.wt  index-*.wt  journal  WiredTiger*  mongod.lock ...
```

!!! warning "Publishing Mongo"

    `-p 27017:27017` binds to every interface and this Mongo had no authentication. Fine behind home NAT, an open database on a cloud VM. Bind to localhost instead: `-p 127.0.0.1:27017:27017`.

### Errors I hit

| Symptom | Cause | Fix |
|---|---|---|
| Data gone after recreating the container | No volume, data was in the container layer | Mount a named volume on the data path (`/data/db` for Mongo) |
| `Permission denied` on `/var/lib/docker/volumes` | Directory is root-only | `sudo ls ...` or `sudo su -` |
| Files from a bind mount are owned by root on the host | Container process runs as root | Run with `--user "$(id -u):$(id -g)"` or `chown` afterwards |
| Empty root-owned folder appears at a typo path | `-v` creates missing host paths | Use `--mount type=bind`, it errors instead |

!!! tip "Quick revision"

    * Volume → Docker-managed, by name, for persistence
    * Bind mount → your host path, for dev files and host resources
    * `--rm` removes the container, never a named volume

!!! question "Interview points"

    * Volume vs bind mount? → a volume is managed by Docker and referenced by name, a bind mount maps a host path you choose. Volumes for persistent app data, bind mounts for dev code and config
    * Container was deleted and the data is gone, why? → the data was in the container's writable layer. Mount a volume on the data path
    * Does `--rm` delete a named volume? → no, only the container (and anonymous volumes). Named volumes stay until `docker volume rm`
    * How do you tell `-v` volume from bind mount? → source starting with `/` or `./` is a bind mount, a plain name is a volume
    * Why prefer `--mount` over `-v`? → it is explicit, and it errors on a missing bind source instead of creating an empty directory
    * Files written by a container show up root-owned on the host? → the container runs as root. Use `--user` with the host UID and GID
    * Where are named volumes stored on Linux? → `/var/lib/docker/volumes/<name>/_data`, readable only by root
    * How would you back up a volume? → run a throwaway container that mounts the volume and a host folder, and `tar` the data
    * When would you use `tmpfs`? → temporary or sensitive data you don't want written to disk
