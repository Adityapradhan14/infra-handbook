# Docker

*Hands-on notes, written while learning Docker on my own Ubuntu machine*

<div class="ih-chapters" markdown>

1. [Introduction](introduction.md)
    Container vs VM, namespaces, cgroups, OverlayFS, core objects
2. [Architecture](architecture.md)
    CLI, `docker.sock`, `dockerd`, `containerd`, shim, `runc`
3. [Install & Upgrade](installation.md)
    Install method, upgrading `docker-ce`, socket activation
4. [Containers](containers.md)
    Lifecycle, `docker run` flags, `ps -aq`, stop vs rm, `--rm`
5. [Images & Storage](images-and-storage.md)
    Layers, copy-on-write, tags vs digests, Dockerfile, volumes
6. [Networking](networking.md)
    Ports, `docker0`, drivers, custom networks, DNS, host mode
7. [Namespaces](namespaces.md)
    The 7 namespaces, `nsenter`, `lsns`, `unshare`
8. [Logs & Files on Disk](logs-and-files.md)
    `/var/lib/docker`, the `-json.log` file, `docker logs`
9. [Volumes & Bind Mounts](volumes-and-bind-mounts.md)
    `-v` vs `--mount`, named volumes, bind mounts, `tmpfs`, backup
10. [The Docker Socket](docker-socket.md)
    `docker.sock`, mounting it, why it is root, Portainer
11. [Dockerfile](dockerfile.md)
    `FROM`, `RUN` vs `CMD`, `ARG` vs `ENV`, building and running an image
12. [ENTRYPOINT & CMD](entrypoint-and-cmd.md)
    fixed command vs default arguments, `--entrypoint`, exit codes, main process
13. [EXPOSE, COPY, WORKDIR & USER](expose-copy-workdir-user.md)
    `EXPOSE` vs `-p`, `COPY` vs `ADD`, non-root `USER`, `-f`
14. [Image Layers, Tags & Cleanup](image-layers-and-tags.md)
    layers, build cache, image ID vs tag, `docker history`, prune, secrets

</div>
