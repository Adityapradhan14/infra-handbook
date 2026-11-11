# Image Layers, Tags & Cleanup

*Hands-on notes, Docker images*

## Layers

* An image is a stack of read-only layers → one per instruction that changes files
* `RUN`, `COPY`, `ADD` → add data | `ENV`, `ARG`, `LABEL`, `CMD`, `EXPOSE` → 0B, metadata only
* A container is the image layers plus one thin writable layer on top → why data is lost on `docker rm`, see [volumes](volumes-and-bind-mounts.md)
* Layers are shared between images and containers → a second container from the same image copies nothing
* Deleting a file in a later layer does not shrink the image → remove it in the same `RUN` that created it, or leave the build tools behind with a [multi-stage build](multi-stage-and-distroless.md)
* `docker history aditya/custom:v1` → layers newest first with size and the instruction that made them
* `<missing>` in the `IMAGE` column → normal, those layers have no local image ID of their own
* `docker history --no-trunc` → full instructions, including `ENV` values

```
CMD ["nginx" "-g" "daemon off;"]            0B
RUN |2 T_VERSION=1.5.0 P_VERSION=1.4.0 ...  233MB   ← terraform and packer downloads
RUN |2 T_VERSION=1.5.0 P_VERSION=1.4.0 ...  67.3MB  ← apt install
ARG T_VERSION=1.5.0 P_VERSION=1.4.0         0B
ENV AWS_ACCESS_KEY_ID=...                   0B
LABEL name=Aditya                           0B
(Ubuntu base)                               102MB
```

## Build cache

* Docker reuses a layer when its instruction and everything above it are unchanged
* A change breaks the cache from that line downward
* Put what changes rarely first (`apt install`, dependencies) and what changes often last (your code)
* `--no-cache` → ignore the cache and rebuild everything
* Used `ARG` values are part of the cache key → a new version rebuilds the `RUN` that uses it

| Build | Time | Why |
|---|---|---|
| First `docker build .` | 143.5s | Nothing cached, base image pulled |
| `docker build -t aditya/custom:v1 .` | 1.3s | Every step `CACHED`, same image ID |
| After changing `LABEL` and `--build-arg` | 158.9s | Change sits above the `RUN`s, they rebuilt |

## Image ID vs tag

* ID (`ec7d7ab8c135`) → the identity of the image, a content hash
* Tag (`aditya/custom:v1`) → a movable name that points at an ID
* `docker build -t` on a fully cached build → adds a name to the same ID, no second image is created
* Rebuilding with a change under the same tag → new ID, the tag moves, the old image loses its name
* One image can have several names → `docker tag aditya/custom:v1 aditya/custom:latest`
* `docker rmi <tag>` → removes that name only, the image stays while other names or containers use it
* `latest` is just a default tag name, not "newest" → pin versions

```bash
docker images
docker tag aditya/custom:v1 aditya/custom:v2
docker rmi aditya/custom:v2
docker images --no-trunc
```

## Dangling images and cleanup

* Dangling image → untagged, shown as `<none>` or `<untagged>`, usually the old version after a rebuild
* `docker images -f dangling=true` → list them
* `docker image prune` → delete dangling images only
* `docker system prune` → stopped containers, unused networks, dangling images and unused build cache, asks `y/N`
* Add `-a` to also remove every image no container uses, check first
* `docker system df` → what is using disk
* `docker rmi nginx:latest` → remove a specific image, fails while a container still uses it

!!! warning "Check before pruning"

    My dangling list held two images, the old `aditya/custom` build and an untagged `kindest/node` (974MB). `docker image prune` deleted both, 974.2MB reclaimed. The second was not mine to lose from this build, it just had lost its tag to a newer one. Read the list first.

## Secrets in images

* `ENV` and `ARG` values are stored in the image metadata, not just the running container
* `docker history --no-trunc image` and `docker inspect image` show them
* `docker exec app1 env` listed the baked-in keys in every container started from the image
* `docker run -e AWS_ACCESS_KEY_ID=hidden` → overrides the value in that container, but the original is still inside the image, and other baked values like `AWS_DEFAULT_REGION` remain
* BuildKit warns with `SecretsUsedInArgOrEnv` → this is exactly why
* Pass secrets at run time → `-e NAME` (copies from your shell), `--env-file`, or an IAM role on AWS
* Secrets needed during a build → BuildKit `RUN --mount=type=secret`
* A key that was baked into an image that left your machine → rotate it
* Never commit real keys in Dockerfiles or notes in a public repo

!!! tip "Quick revision"

    * Image ID = identity, tag = a name for it
    * Cache breaks from the first changed line down
    * `docker image prune` = dangling only, read the list first
    * Secrets: runtime, never `ENV`

!!! question "Interview points"

    * What is an image layer? → a read-only filesystem diff made by an instruction like `RUN` or `COPY`, stacked to form the image and shared between images
    * Which instructions make the image bigger? → `RUN`, `COPY`, `ADD`. `ENV`, `ARG`, `LABEL`, `CMD` are 0B metadata
    * How does the build cache work? → a layer is reused if its instruction and all earlier layers are unchanged. The first change invalidates everything below it
    * How do you order a Dockerfile for fast rebuilds? → rarely changing steps first (base, packages, dependencies), frequently changing steps (your code) last
    * Does deleting a file in a later layer reduce image size? → no, the earlier layer still holds it. Delete in the same `RUN`
    * Image ID vs tag? → the ID identifies the image content, a tag is a movable name. Rebuilding under the same tag moves the tag to a new ID
    * What is a dangling image and how do you remove it? → an untagged image left behind when a tag moves. `docker image prune`
    * What does `docker system prune` remove? → stopped containers, unused networks, dangling images and unused build cache
    * Why are secrets in `ENV` bad, and what do you do instead? → they are stored in the image and visible via `docker history` and `docker inspect`. Pass them at run time or use an IAM role, and rotate any key that was baked in
    * What does `<missing>` mean in `docker history`? → those layers have no local image ID, which is normal for layers from a base image or BuildKit
