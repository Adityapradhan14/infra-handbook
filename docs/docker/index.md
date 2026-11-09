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
    Ports, `docker0`, veth pairs, NAT, `-p` port forwarding
7. [Namespaces](namespaces.md)
    The 7 namespaces, `nsenter`, `lsns`, `unshare`
8. [Logs & Files on Disk](logs-and-files.md)
    `/var/lib/docker`, the `-json.log` file, `docker logs`

</div>
