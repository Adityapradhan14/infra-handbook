# Multi-Stage Builds & Distroless

*Hands-on notes, Spring PetClinic image*

## Distroless

* Distroless image → only your app and its runtime, no OS userland → no shell, no package manager, no `ls`, `curl`, `apt`
* Maintained by Google → `gcr.io/distroless/...`
* A normal `ubuntu` or `debian` base ships hundreds of tools the app never uses
* Fewer packages → fewer CVEs for scanners, smaller image, and an attacker who gets code execution has no shell or `curl` to work with
* `gcr.io/distroless/static` → static binaries (Go, Rust), `static-debian13` pulled at 2.37MB
* `gcr.io/distroless/base` → adds glibc
* `gcr.io/distroless/java17-debian12`, `python3`, `nodejs22` → language runtimes
* Tags → `:nonroot` runs as UID 65532, `:debug` adds a busybox shell for troubleshooting only
* `scratch` → completely empty image, static binaries only | `alpine` → small but has a shell and `apk`, uses musl instead of glibc
* Cost → no `docker exec -it c bash`, no `RUN apt install` in the final stage, exec-form `CMD` and `ENTRYPOINT` only because shell form needs `/bin/sh`
* Debugging → `:debug` tag in dev, `kubectl debug` with an ephemeral container in Kubernetes

## Multi-stage build

* Several `FROM` lines in one Dockerfile → each starts a new stage
* `FROM image AS build` → names a stage
* `COPY --from=build /app/app.jar app.jar` → copies a file out of an earlier stage
* Only the last stage becomes the image → the JDK, Maven, source and caches of earlier stages are left behind
* Pattern → fat stage with the toolchain builds, slim stage only runs
* `docker build --target build -t pc-build .` → stop at one stage, useful to inspect what the build produced
* Layers of the build stage still sit in the local cache → rebuilds stay fast, they just do not ship

```dockerfile
# Stage 1: build
FROM eclipse-temurin:17-jdk AS build
WORKDIR /app
COPY . .
RUN ./mvnw package -DskipTests && cp target/*.jar app.jar

# Stage 2: runtime (distroless, no shell, non-root)
FROM gcr.io/distroless/java17-debian12:nonroot
WORKDIR /app
COPY --from=build /app/app.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```

* `cp target/*.jar app.jar` runs inside `RUN`, which has a shell, so the `*` expands and the jar gets a fixed name
* The final stage then uses that name → no glob in exec form
* `ENTRYPOINT` rather than `CMD` → the image only ever runs this one thing, see [ENTRYPOINT & CMD](entrypoint-and-cmd.md)
* Runtime Java must be the same or newer than the build Java → a jar built on 17 does not run on 11

## Lab: Spring PetClinic

* Cloned `spring-projects/spring-petclinic`, wrote a single-stage Dockerfile first, then the multi-stage one

```bash
git clone https://github.com/spring-projects/spring-petclinic.git
cd spring-petclinic
docker build -t petclinic .
docker run --rm -d --name petclinic -p 8080:8080 petclinic
docker logs -f petclinic
```

| Image | Base | Size | Build |
|---|---|---|---|
| `petclinic` single-stage | `eclipse-temurin:17-jdk` | 750MB | 296s, 105s of it pulling the base |
| `new-distro` multi-stage | `gcr.io/distroless/java17-debian12:nonroot` | 292MB | 211s, `mvnw package` 207s |
| `distroless/static-debian13` alone | none | 2.37MB | pulled only |

* About 60% smaller → the single-stage image carries the JDK, the source and the Maven cache, the final stage only the JRE and one jar
* Log of the running distroless container → `PID 1`, `started by nonroot in /app`, Java 17.0.18, Spring Boot 4.1.0, Tomcat on 8080, `Started PetClinicApplication in 6.53 seconds`
* Non-root works here because the app listens on 8080, a port above 1024
* `RUN ./mvnw package` ran again on every rebuild (172s to 207s) → most likely because `COPY . .` copies the whole folder, Dockerfiles included, so any edit there breaks the cache from that line down

### Proof that distroless has no shell

* Used `static-debian13` as the base of the earlier tools image and kept `RUN apt update && apt install ...`

```
runc run failed: unable to start container process: error during container init:
exec: "/bin/sh": stat /bin/sh: no such file or directory
```

* `RUN` needs `/bin/sh` → with no shell in the image, even the build step cannot start
* Fix → do all `RUN` work in a build stage and `COPY --from` the result

### Errors I hit

| Symptom | Cause | Fix |
|---|---|---|
| `docker build requires 1 argument` | Typed `docker build -t petclinic Dockerfile .`, two paths | `docker build -t petclinic .`, or `-f Dockerfile .` |
| `unknown shorthand flag: 'r'` | `-r` does not exist, the flag is `-f` | `docker build -f dockerfile.new -t x .` |
| `openjdk:17-jdk-slim: not found` | The `openjdk` image was removed from Docker Hub | `eclipse-temurin:17-jdk` |
| `open dockerfil.new: no such file or directory` | Typo in the `-f` name | Tab completion |
| `docker ps` empty after `run -d --rm` | The app crashed at start and `--rm` removed it | Run in the foreground without `-d` and `--rm` |
| `Error: Unable to access jarfile target/*.jar` | Exec-form `CMD` does not expand `*` | `cp target/*.jar app.jar` in a `RUN`, `ENTRYPOINT ["java","-jar","app.jar"]` |
| `exec: "/bin/sh": stat /bin/sh: no such file` | `RUN` in a distroless stage | Move the `RUN` to a build stage |

### Things to improve

* Copy `pom.xml` and the Maven wrapper first, run `./mvnw dependency:go-offline`, then `COPY src` → dependencies stay cached when only code changes
* Add a `.dockerignore` with `target/`, `.git`, `*.md`, the extra Dockerfiles → smaller context, fewer cache busts
* Pin tags more tightly or by digest → `latest`-style moves break builds
* Use a JRE-only build stage image if the project allows it, and Java 21 if the Spring Boot version asks for it

!!! tip "Quick revision"

    * Multi-stage → many `FROM`, last one ships, `COPY --from=name` pulls files across
    * Distroless → no shell, no package manager, small and low-CVE
    * `RUN` needs `/bin/sh` → do it in the build stage
    * `:nonroot` for the user, `:debug` for a shell while troubleshooting

!!! question "Interview points"

    * What is a multi-stage build? → several `FROM` stages in one Dockerfile, a heavy stage compiles the app and the last, slim stage copies only the artifact with `COPY --from`
    * Why use it? → the final image has no compiler, source or build cache, so it is smaller and has a smaller attack surface
    * What is a distroless image? → a base with the app runtime only, no shell, no package manager, no OS tools
    * Benefits of distroless? → fewer CVEs, smaller image, an attacker who gets in has no shell or `curl` to use
    * Downsides? → no `docker exec` shell, no `RUN apt install` in the final stage, only exec-form `CMD` and `ENTRYPOINT`, debugging needs the `:debug` tag or an ephemeral container
    * Why did `RUN apt update` fail on a distroless base? → `RUN` starts `/bin/sh -c` and the image has no `/bin/sh`
    * How do you debug a distroless container in Kubernetes? → `kubectl debug` with an ephemeral container that shares the pod's namespaces
    * `distroless` vs `scratch` vs `alpine`? → `scratch` is empty and only fits static binaries, distroless adds CA certs, timezone data and a non-root user, `alpine` is small but has a shell and uses musl
    * How do you harden an image? → multi-stage build, minimal or distroless base, non-root `USER`, pinned versions, no secrets in `ENV`
    * What does `docker build --target` do? → builds only up to the named stage and tags that
