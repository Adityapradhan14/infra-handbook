# EXPOSE, COPY, WORKDIR & USER

*Hands-on notes, building images*

## EXPOSE

* `EXPOSE 80` → documents the port the app listens on, nothing else
* It does not publish the port → `-p HOST:CONTAINER` does that
* `docker run -P` (capital) → publishes every `EXPOSE`d port to a random host port, the only place `EXPOSE` changes behaviour
* `-p 8080:80` works without `EXPOSE`, and `EXPOSE` without `-p` is not reachable from the host
* `-p` always wins → `EXPOSE 80` with `-p 8000:8000` forwards host 8000 to container 8000, nothing checks it against `EXPOSE`
* The container side of `-p` must be the port the app really binds → app on 80 needs `-p 8000:80`
* The app must listen on `0.0.0.0`, not `127.0.0.1`, or `-p` has nothing to reach
* Containers on the same network reach any listening port, `EXPOSE` or not
* `docker inspect` keeps the two apart → `Config.ExposedPorts` is the note, `HostConfig.PortBindings` is what `-p` created

```bash
docker run --rm -d --name expose -p 80:80 app5       # host 80 → container 80
docker run --rm -d --name appx   -p 8000:80 copy     # same image port 80, different host port
docker ps                                            # 0.0.0.0:8000->80/tcp, [::]:8000->80/tcp
```

## COPY vs ADD

* `COPY src dest` → copies from the build context into the image
* `ADD` → same, plus it extracts local tarballs (`.tar`, `.tar.gz`, `.tar.xz`) and accepts URLs
* A URL given to `ADD` is downloaded, not extracted → the `.zip` just sits in the image
* Prefer `COPY` → `ADD` has hidden behaviour
* For downloads use `RUN wget ... && unzip ... && rm ...` → download, extract and delete in one layer
* The source must be inside the build context → `COPY ../file .` fails
* `COPY dir /dest` copies the contents of `dir`, not the folder itself
* A destination ending in `/` is a directory
* `COPY --chown=user:group` → files are owned by root otherwise
* Put what changes rarely first so the cache survives → `COPY package.json` and install, then `COPY . .`

```dockerfile
COPY index.nginx-debian.html /var/www/html/
COPY scorekeeper.js /var/www/html/
COPY style.css /var/www/html/
```

* `ADD https://releases.hashicorp.com/terraform/1.9.0/terraform_1.9.0_linux_amd64.zip /var/www/html` took 14.7s on the first build and was `CACHED` after → it only put a zip in the web root
* Image sizes → `copy` image (with the `ADD`) 486MB, `app5` 459MB, cleaned `dev` image 357MB

## WORKDIR

* `WORKDIR /app` → working directory for every later `RUN`, `COPY`, `ADD`, `CMD`, `ENTRYPOINT`, and for `docker exec`
* Created if missing, no `RUN mkdir` needed
* Relative paths stack → `WORKDIR /a` then `WORKDIR b` is `/a/b`
* `RUN cd /app` only lasts for that one line, `WORKDIR` stays
* `docker run -w /other` overrides it
* Default is `/`, which is why Terraform and Packer landed in `/` before `WORKDIR` was added
* After `WORKDIR /app` the downloads ended up there → `docker exec -it last bash` opened in `/app` and `ls` showed `packer  terraform`

## USER

* `USER appuser` → every later instruction and the running container use that user, default is `root`
* Root-only steps (`apt install`) must come before `USER`
* The user must exist first → `RUN groupadd appuser && useradd -r -g appuser appuser`
* `useradd -r` makes a system user with a nologin shell → `su -s /bin/bash appuser` to switch into it
* Can be a number → `USER 1000`, Kubernetes `runAsNonRoot` needs a numeric UID
* `docker run -u root` or `docker exec -u appuser` override it
* Why → a compromised process as root is root inside the container, with mounted volumes and escapes it does far more damage
* Non-root cannot bind ports below 1024, cannot write `/var/log/nginx`, `/run/nginx.pid` or nginx's temp dirs → nginx on port 80 needs root, or listen on 8080 with a config that points those paths at writable folders

## Custom Dockerfile name

* Default lookup is `Dockerfile`, lowercase `dockerfile` is also accepted on Linux
* `docker build -f dockerfile.dev -t dev .` → any file name, the extension does not matter
* `.` is the build context, separate from the Dockerfile location
* Editors only highlight `Dockerfile`, `Dockerfile.dev` and `dev.Dockerfile`
* Compose → `build: { context: ., dockerfile: dockerfile.dev }`

## Lab: running as a non-root user

* First attempt had `USER appuser` above the `apt` step, so the build failed

```bash
docker build -t dev -f dockerfile.dev .
```

```
Error: List directory /var/lib/apt/lists/partial is missing. - Acquire (13: Permission denied)
ERROR: failed to build: ... exit code: 100
```

* Fix → install as root first, create the user and set `WORKDIR` after, drop `USER` for nginx on port 80
* Build then took 72s, nothing cached, image 357MB
* Testing the user from inside the running container:

```bash
docker run --rm -d --name last -p 8005:80 dev:latest
docker exec -it last bash          # opens as root in /app
su -s /bin/bash appuser
touch /app/test                    # Permission denied
exit
docker stop last
```

* Other ways to see it without editing the Dockerfile → `docker run --rm -u appuser dev whoami`, `docker exec -u appuser last bash`
* Running nginx itself as `appuser` shows the next errors → `/var/log/nginx/error.log` and `/run/nginx.pid` permission denied, then port 80 `bind()` denied

### Errors I hit

| Symptom | Cause | Fix |
|---|---|---|
| `apt` `Permission denied`, exit code 100 | `USER appuser` placed before `RUN apt install` | Root steps first, `USER` last |
| `su appuser` gives no shell | `useradd -r` sets a nologin shell | `su -s /bin/bash appuser` |
| `touch: cannot touch '/app/test'` as `appuser` | `/app` was created by root | `COPY --chown`, or `chown` it before `USER` |
| `docker exec requires at least 2 arguments` | No command after the container name | `docker exec -it last bash` |
| Own `index.html` replaced by the default page | `COPY` ran before `apt install nginx`, the package ships its own file at that path | Install first, `COPY` the site after |
| `SecretsUsedInArgOrEnv` warning | AWS keys in `ENV` | Remove, pass with `docker run -e`, see [image layers and tags](image-layers-and-tags.md) |

!!! tip "Quick revision"

    * `EXPOSE` → note, `-p` → real, `-P` → all `EXPOSE`d to random ports
    * `COPY` by default, `ADD` only for local tarballs
    * `WORKDIR` → persists, `RUN cd` does not
    * `USER` goes after the root steps, nginx on 80 needs root

!!! question "Interview points"

    * Does `EXPOSE` publish a port? → no, it documents it, `-p` publishes, `-P` publishes all `EXPOSE`d ports to random host ports
    * `EXPOSE 80` and `-p 8000:8000`, what happens? → `-p` wins, host 8000 goes to container 8000, if the app listens on 80 the connection fails with no warning
    * `COPY` vs `ADD`? → `ADD` also extracts local tarballs and downloads URLs, a downloaded archive is not extracted, use `COPY` and `RUN curl` instead
    * Why `WORKDIR` instead of `RUN cd`? → `cd` lasts one `RUN`, `WORKDIR` applies to every later instruction and to the running container
    * Why run as non-root? → a breakout or a bug then gives an unprivileged user, not root
    * Build fails with `Permission denied` in `apt`, why? → `USER` was set before the install, root-only steps must run first
    * Can a non-root user run nginx on port 80? → not by default, ports below 1024 need root or a capability, use 8080
    * How do you build with a differently named Dockerfile? → `docker build -f name -t tag .`, the `.` stays the context
    * Why are secrets in `ENV` bad? → they are baked into the image layers and show up in `docker inspect` and `docker history`
