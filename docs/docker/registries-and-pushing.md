# Registries & Pushing Images

## What a registry is

* **Registry** → server that stores and serves images → like an app store for images
* **Repository** → one image's collection of versions inside a registry → `nginx`, `myuser/my-app`
* **Tag** → one version inside a repository → `1.27`, `v1.0`, `latest`
* Public → Docker Hub (`docker.io`), GitHub Container Registry (`ghcr.io`), Quay (`quay.io`)
* Cloud / private → AWS ECR, Google Artifact Registry / GCR, Azure ACR, JFrog Artifactory, Nexus, self-hosted Harbor
* Flow → build image locally → **push** to a registry → servers and Kubernetes nodes **pull** from it

## Anatomy of a full image name

```
docker.io / library / ubuntu : latest
registry    namespace  repo    tag
```

* `docker pull ubuntu` → Docker fills in the rest → `docker.io/library/ubuntu:latest`
* No registry given → Docker Hub (`docker.io`)
* No namespace on Docker Hub → `library` = official images
* No tag → `latest` → just a default tag name, not "newest" → pin real tags in production
* Digest (`@sha256:...`) → exact, unchangeable content | tags can be moved to a new image

| Registry | Name format | Example |
|---|---|---|
| Docker Hub | `docker.io/<user>/<repo>:<tag>` | `docker.io/myuser/my-app:v1.0` |
| AWS ECR | `<account-id>.dkr.ecr.<region>.amazonaws.com/<repo>:<tag>` | `123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:v1.0` |
| Google GCR | `gcr.io/<project-id>/<image>:<tag>` | `gcr.io/my-gcp-project/my-app:v1.0` |
| Google Artifact Registry | `<region>-docker.pkg.dev/<project>/<repo>/<image>:<tag>` | `us-central1-docker.pkg.dev/my-proj/apps/my-app:v1.0` |
| GitHub | `ghcr.io/<user>/<image>:<tag>` | `ghcr.io/myuser/my-app:v1.0` |

* `docker pull` works the same everywhere → only the full name changes
* Private registries → log in first

## Logging in

```bash
docker login                                  # Docker Hub, asks for username + access token
docker login ghcr.io
aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com
docker logout
```

* Use an **access token**, not the account password
* Credentials saved in `~/.docker/config.json` → base64 only unless a credential helper is configured → treat it like a password file

## Build, tag, push

```dockerfile
FROM ubuntu:latest
CMD echo "Hello, Docker!"
```

```bash
docker build -t my-first-image .                          # . = build context
docker run my-first-image                                 # Hello, Docker!
docker tag my-first-image <username>/my-first-image:v1.0  # new name for the same image
docker images                                             # both names, same IMAGE ID
docker push <username>/my-first-image:v1.0                # really docker.io/<username>/my-first-image:v1.0
docker pull <username>/my-first-image:v1.0                # from any machine
```

* `docker tag` → does not copy anything → adds another name pointing to the same image ID
* Push needs the name to include **my namespace** → `docker push my-first-image` fails, Docker Hub's `library/` is only for official images
* Push sends only layers the registry doesn't already have → shared base layers are skipped ("Layer already exists")
* Tag with a real version (`v1.0`, git SHA) → `latest` can't be rolled back to

## Custom Dockerfile name and build context

```bash
docker build -t my-app -f Dockerfile.prod .
docker build -t entry-image -f /path/to/custom-dockerfile /path/to/build-context
```

* `-f` → which Dockerfile to use (e.g. `Dockerfile.dev`, `Dockerfile.prod`)
* Last argument → **build context** → the folder sent to the daemon → `COPY`/`ADD` can only see files inside it
* `.dockerignore` → keep `.git`, `node_modules`, secrets out of the context

## Everyday commands

| Command | Does |
|---|---|
| `docker images` | List local images |
| `docker ps -a` | All containers, including stopped |
| `docker inspect <id>` | Full metadata of a container or image |
| `docker top <container>` | Processes inside a running container |
| `docker stop $(docker ps -q)` | Stop all running containers |
| `docker container prune` | Delete all stopped containers |
| `docker rmi <image>` | Delete an image |
| `docker image prune -a` | Delete all images not used by a container |

!!! question "Interview points"

    * Registry vs repository vs tag? → a registry is the server, a repository is one image's set of versions, a tag is one version
    * What does docker pull ubuntu actually pull? → docker.io/library/ubuntu:latest
    * Does latest mean the newest version? → no, it is just the default tag name; pin explicit tags or digests in production
    * Tag vs digest? → a tag is a movable label; a digest is the sha256 of the content and never changes
    * Why does docker push my-first-image fail on Docker Hub? → the image name needs your namespace, e.g. username/my-first-image
    * What does docker tag do? → adds another name to the same image ID, nothing is copied
    * How do you push to ECR? → get a token with aws ecr get-login-password, docker login to the account's registry URL, tag with the full ECR name, push
    * What is the build context? → the folder sent to the daemon during docker build; COPY and ADD only see files inside it, and .dockerignore trims it
