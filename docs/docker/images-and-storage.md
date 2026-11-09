# Images & Storage

*Hands-on notes, image layers and where container data lives*

## Layers

* Image → stack of read-only layers
* Each filesystem-changing Dockerfile instruction (`RUN`, `COPY`, `ADD`) → one new layer holding only what changed
* Layers are shared → 10 images on `ubuntu:24.04` store that layer once
* Layer ID → hash of its contents (sha256) → same content = same hash

```
Layer 4: COPY app.py              (my 5 KB file)
Layer 3: RUN pip install flask    (flask files)
Layer 2: RUN apt install python3  (python files)
Layer 1: FROM ubuntu:24.04        (base OS files)
```

## Writable layer and copy-on-write

* Running a container → Docker adds one thin writable layer on top
* OverlayFS merges all layers into the one `/` the container sees → top-most file wins
* Reading → found in whichever layer has it
* Changing a file from a lower layer → copied up into the writable layer first, then modified → copy-on-write → image untouched
* Deleting → "whiteout" marker hides it → still exists in the lower layer, image doesn't shrink
* Delete the container → writable layer gone with all its data → databases need volumes

## Names, tags and digests

* Full name → `registry/namespace/repository:tag`
* `nginx` → short for `docker.io/library/nginx:latest`
* `latest` → just a default tag name, NOT "newest" → don't rely on it for real work
* Tag → mutable, can be moved to another image
* Digest → `nginx@sha256:...` → immutable, always the exact same image

## Dockerfile instructions

| Instruction | What it does | Layer? |
|---|---|---|
| `FROM` | Base image | Starts the stack |
| `RUN` | Command at build time (install packages) | Yes |
| `COPY` | Files from my machine into the image | Yes |
| `ADD` | COPY + URL/tar extraction (prefer COPY) | Yes |
| `WORKDIR` | Current directory | Metadata |
| `ENV` | Environment variables | Metadata |
| `EXPOSE` | Documents a port, does NOT open it | Metadata |
| `USER` | User the app runs as | Metadata |
| `CMD` | Default command when the container starts | Metadata |
| `ENTRYPOINT` | Fixed main executable, CMD becomes its arguments | Metadata |

* `RUN` → once, while building | `CMD` → every time a container starts
* Only `CMD ["nginx", "-g", "daemon off;"]` → `docker run img bash` replaces it
* `ENTRYPOINT ["ping"]` + `CMD ["google.com"]` → `docker run img 8.8.8.8` runs `ping 8.8.8.8` → only CMD replaced
* nginx image → ENTRYPOINT `/docker-entrypoint.sh` runs setup scripts, then starts nginx

## Build cache, context, multi-stage

* Each layer is cached → unchanged instruction + inputs → reused instantly
* One layer changes → every layer after it rebuilds → rarely-changing things (dependencies) first, code last
* `docker build .` → `.` = build context, folder sent to the builder → `COPY` only sees files inside it
* `.dockerignore` → exclude `node_modules`, `.git` → faster builds, no leaked secrets
* Multi-stage → build in one stage with compilers, copy only the final binary into a small second stage

## Storage

| Type | Where data lives | Use for | Example |
|---|---|---|---|
| Volume | `/var/lib/docker/volumes/<name>/`, managed by Docker | Databases, anything persistent | `-v pgdata:/var/lib/postgresql/data` |
| Bind mount | Any host folder I choose | Dev: edit on host, container sees it live | `-v $(pwd):/app` |
| tmpfs | RAM only, gone on stop | Secrets, scratch | `--tmpfs /tmp` |

* `-v` left side starts with `/` or `./` → bind mount | just a name → volume
* Mounting over a folder hides what the image had there
* Volume survives `docker rm` | writable layer doesn't

## Lab: first pull

```bash
docker run --name app1 nginx:latest
docker images
docker system df
```

* `Unable to find image 'nginx:latest' locally` → `dockerd` checked local storage
* `Pulling from library/nginx` → went to Docker Hub
* 7 × `Pull complete` → 7 image layers downloaded
* `Digest: sha256:...` → the exact image `latest` pointed to at that moment
* Only the first pull is slow (~64 MB here) → layers cached → next run starts in about a second

| Symptom | Cause | Fix |
|---|---|---|
| Same layers downloading again minutes later | Image deleted, or that terminal talks to a different daemon/context | Compare `docker context ls`, `docker info`, `docker images` in both terminals |
| Pull feels slow | Cloudflare WARP tunnel (MTU 1300, extra hop) | `time docker pull` with and without `warp-cli disconnect` |

!!! question "Interview points"

    * What is an image layer? → a read-only slice of the filesystem created by RUN, COPY or ADD, identified by a content hash
    * What is copy-on-write? → changing a file from a lower layer copies it up into the container's writable layer first; the image is never modified
    * Why doesn't deleting a file in a later layer shrink the image? → it only adds a whiteout marker; the file still exists in the earlier layer
    * Does latest mean newest? → no, it is just a default tag name that can point anywhere
    * Tag vs digest? → tag is mutable, digest (sha256) always points to the exact same image
    * RUN vs CMD? → RUN executes at build time; CMD is the default command each time a container starts
    * CMD vs ENTRYPOINT? → ENTRYPOINT is the fixed executable; CMD supplies default arguments that docker run can replace
    * Does EXPOSE publish a port? → no, it only documents it; only -p publishes
    * Why order Dockerfile instructions carefully? → a changed layer invalidates the cache for every layer after it
    * Volume vs bind mount? → volume is managed by Docker under /var/lib/docker/volumes; bind mount maps a host path I choose
    * Where does container data go when the container is removed? → the writable layer is deleted; only volumes and bind mounts survive
