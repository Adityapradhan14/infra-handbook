# Dockerfile

*Hands-on notes, building images*

## What it is

* Dockerfile → a text file of instructions that tells Docker how to build an image
* Image → the finished read-only package | container → a running instance of an image
* `docker build -t name:tag .` → build from the Dockerfile in the current folder, the `.` is the build context
* `docker build` only creates an image → nothing runs, `docker ps -a` stays empty until `docker run`

## Instructions

* `FROM` → base image to start from, always first → `FROM ubuntu:24.04`
* `LABEL` → metadata only → `LABEL name="aditya"`
* `ENV` → environment variable, present at build time and in every container, baked into the image
* `ARG` → build-time variable only, set with `--build-arg`, gone when the container runs
* `RUN` → run a command at build time, the result is saved as a layer → `RUN apt update && apt install -y nginx`
* `COPY` → copy files from the build context into the image
* `ADD` → like `COPY` but also extracts tarballs and fetches URLs, prefer `COPY`
* `WORKDIR` → set the working directory, created if missing
* `EXPOSE` → documents the port the app uses, does not publish it, `-p` does
* `USER` → run the rest as a non-root user
* `CMD` → default command when a container starts, only the last one counts, `docker run image other-cmd` overrides it
* `ENTRYPOINT` → fixed command, `CMD` then becomes its default arguments
* `.dockerignore` → paths left out of the build context → `.git`, `.venv`, `.env`

## RUN vs CMD

* `RUN` → executes while the image is being built
* `CMD` → only recorded during the build, executes when a container starts from the image
* After `docker build` finishes nothing is running, the image is just a file on disk
* Never start a long-running process in `RUN` → the build would hang
* Each `docker run` starts `CMD` again, `RUN` happened once

```dockerfile
FROM alpine
RUN echo "building"
CMD ["echo", "running"]
```

```bash
docker build -t t1 .          # prints "building" once
docker run --rm t1            # prints "running"
docker run --rm t1 echo hi    # overrides CMD, prints "hi"
```

## CMD forms and the foreground rule

* Exec form → `CMD ["nginx","-g","daemon off;"]` runs `nginx` directly as the main process, signals from `docker stop` reach it
* Shell form → `CMD nginx -g "daemon off;"` wraps it in `/bin/sh -c`
* A container lives only as long as its main process
* nginx forks into the background by default → the first process exits and the container stops
* `-g "daemon off;"` → global directive that keeps nginx in the foreground
* The official `nginx` image already sets this → needed when you install nginx on `ubuntu` yourself

```bash
docker run --rm -d --name n1 nginx nginx -g "daemon off;"   # stays up
docker run --rm -d --name n2 nginx nginx                    # exits right away
```

## ARG vs ENV

* `ARG` → build time only | `ENV` → build time and run time
* `--build-arg` belongs to `docker build`
* `-e` belongs to `docker run`
* Changing an `ARG` value changes the `RUN` layers that use it, so they rebuild
* Versions that are downloaded during the build must be changed at build time, an env var at run time is too late

```bash
docker build -t aditya/custom:v2 --build-arg T_VERSION=1.5.0 --build-arg P_VERSION=1.4.0 .
```

## Lab: devops tools image

* Ubuntu base, installs `jq`, `net-tools`, `curl`, `wget`, `unzip`, `nginx`, `iputils-ping`
* Downloads Terraform and Packer from HashiCorp with versions from `ARG`
* Runs nginx in the foreground

```dockerfile
FROM ubuntu:latest

LABEL name="aditya"

ENV AWS_ACCESS_KEY_ID=XXXXXXXXXXXXXXXXXXXX \
    AWS_SECRET_KEY_ID=XXXXXXXXXXXXXXXXXXXX \
    AWS_DEFAULT_REGION=US-EAST-1A

ARG T_VERSION='1.6.6' \
    P_VERSION='1.8.0'

RUN apt update && apt install -y jq net-tools curl wget unzip \
    && apt install -y nginx iputils-ping

RUN wget https://releases.hashicorp.com/terraform/${T_VERSION}/terraform_${T_VERSION}_linux_amd64.zip \
    && wget https://releases.hashicorp.com/packer/${P_VERSION}/packer_${P_VERSION}_linux_amd64.zip \
    && unzip terraform_${T_VERSION}_linux_amd64.zip && unzip packer_${P_VERSION}_linux_amd64.zip \
    && chmod 777 terraform && chmod 777 packer \
    && ./terraform version && ./packer version

CMD ["nginx","-g","daemon off;"]
```

```bash
docker build .                                     # image with no name, ~143s the first time
docker ps -a                                       # empty, build creates no container
docker build -t aditya/custom:v1 .                 # 1.3s, every step CACHED, same image ID
docker run --rm -d --name app1 -p 8000:80 aditya/custom:v1
docker exec -it app1 bash                          # shell inside the running container
docker exec app1 packer version
docker stop app1
```

* The two `RUN` steps showed up as `[2/3]` and `[3/3]` → only they and `FROM` are build steps with real work, `ENV`, `ARG`, `LABEL`, `CMD` add no data
* `ls /` inside the container showed `terraform`, `packer` and both `.zip` files → no `WORKDIR`, so everything landed in `/`
* Two containers from one image → `-p 8000:80` and `-p 8001:80`, same port 80 inside, different host ports

### Errors I hit

| Symptom | Cause | Fix |
|---|---|---|
| `unknown flag: --build-arg` on `docker run` | `--build-arg` is a build flag | Rebuild with `docker build --build-arg ... -t new-tag .` |
| `docker ps` and `docker ps -a` empty after `docker build` | A build makes an image, not a container | `docker run` it |
| 233MB layer and `.zip` files still in `/` | Downloads were never removed | `rm -f *.zip` in the same `RUN`, or `unzip -d /usr/local/bin` |
| `SecretsUsedInArgOrEnv` warning during build | Keys set with `ENV` | Remove them, pass at run time, see [image layers and tags](image-layers-and-tags.md) |

### Things to fix in this Dockerfile

* Secrets in `ENV` → remove, use `docker run -e` or an IAM role
* Variable name → `AWS_SECRET_ACCESS_KEY`, not `AWS_SECRET_KEY_ID`
* Region → `us-east-1`, `US-EAST-1A` is an availability zone
* `chmod 777` → `chmod +x` is enough
* `ubuntu:latest` → pin a version such as `ubuntu:24.04`
* Install to `/usr/local/bin` and delete the zips in the same `RUN`
* Clean the apt cache in the same `RUN` → `rm -rf /var/lib/apt/lists/*`

!!! tip "Quick revision"

    * `RUN` → build time, `CMD` → container start
    * `ARG` → build only, `ENV` → build and run
    * `--build-arg` → `docker build`, `-e` → `docker run`
    * Main process in the foreground or the container exits

!!! question "Interview points"

    * Dockerfile vs image vs container? → the Dockerfile is the instructions, the image is what they build, a container is a running instance of the image
    * `RUN` vs `CMD`? → `RUN` executes at build time and saves a layer, `CMD` is stored in the image and executes each time a container starts
    * `CMD` vs `ENTRYPOINT`? → `ENTRYPOINT` is the fixed executable, `CMD` supplies default arguments and is easy to override with `docker run`
    * `ARG` vs `ENV`? → `ARG` exists only during the build, `ENV` is also set in running containers
    * Why does `docker run --build-arg` fail? → `--build-arg` is a `docker build` option, `ARG` values are fixed once the image is built
    * Why does nginx need `daemon off;`? → a container stops when its main process exits, and nginx backgrounds itself by default
    * Exec form vs shell form of `CMD`? → exec form runs the program directly as the main process, shell form wraps it in `/bin/sh -c`
    * Does `EXPOSE` publish a port? → no, it only documents it, `-p` publishes it
    * `COPY` vs `ADD`? → `ADD` also extracts archives and downloads URLs, `COPY` is simpler and preferred
    * What does `.dockerignore` do? → keeps files like `.git` and `.env` out of the build context so they are not sent to the daemon or copied in
