# ENTRYPOINT & CMD

*Hands-on notes, building images*

## The two

* `ENTRYPOINT` → the fixed executable, always runs
* `CMD` → the default command, or the default arguments when an `ENTRYPOINT` exists
* `docker run image something` → `something` replaces `CMD`, with an `ENTRYPOINT` it is appended to it
* `docker run --entrypoint other image` → the only way to replace the `ENTRYPOINT`
* Only the last `CMD` and the last `ENTRYPOINT` in a Dockerfile count
* `ENTRYPOINT` is the program, `CMD` is its default arguments

| Dockerfile | `docker run img` | `docker run img x` |
|---|---|---|
| `CMD ["echo","hello"]` | `echo hello` | `x` runs instead, so `x` must be a full command |
| `ENTRYPOINT ["echo"]` | `echo` | `echo x` |
| `ENTRYPOINT ["python","app.py"]` + `CMD ["--port","8000"]` | `python app.py --port 8000` | `python app.py x` |

* Use exec form (`["a","b"]`) for both → shell form wraps the program in `/bin/sh -c`, it is not PID 1 and misses `SIGTERM` from `docker stop`
* Shell-form `ENTRYPOINT` ignores `CMD` and the arguments from `docker run`
* Kubernetes names → `command` replaces `ENTRYPOINT`, `args` replaces `CMD`
* `ENTRYPOINT` for an image that is a tool (`kubectl`, a wrapper script that ends in `exec "$@"`), `CMD` for a default people swap out (`bash`), both for an app with default flags

## Lab: ping image

* `ENTRYPOINT` is `ping`, `CMD` is the default host
* Only the host is passed at `docker run`, never the command

```dockerfile
ENTRYPOINT ["/usr/bin/ping","-c 4"]
CMD ["www.google.com"]
```

```bash
docker run app3                        # 4 pings to www.google.com, exits 0
docker run app3 www.youtube.com        # CMD replaced, pings youtube instead
docker run app3 ping www.youtube.com   # fails, exits 2
docker ps -a                           # COMMAND column: /usr/bin/ping '-c 4…
```

* The failing run became `/usr/bin/ping -c 4 ping www.youtube.com` → `ping` was treated as a hostname → `No address associated with hostname`
* Same extra `ping` on an image with only `CMD ["ping", ...]` worked and kept pinging until `Ctrl+C` → the whole `CMD` was replaced by `ping www.youtube.com`
* `"-c 4"` as one string worked, but `["/usr/bin/ping","-c","4"]` is the correct form → one argument per element
* Exit codes → `0` success, `2` ping could not resolve or reach the host

## A container lives as long as its main process

* With the `ping` `ENTRYPOINT`, `docker run --rm -d --name expose -p 80:80 app4` → ping ran 4 times and finished
* `docker ps` and `docker ps -a` were both empty → the container exited and `--rm` removed it
* Nothing listened on port 80 → nginx was installed but never started
* Fix → drop the `ping` `ENTRYPOINT` and end the Dockerfile with `CMD ["nginx","-g","daemon off;"]`
* `docker inspect expose` after the fix → `Path` is `nginx`, `Args` is `-g`, `daemon off;`, `Config.Entrypoint` is `null`
* `docker inspect` also showed the `ENV` values in `Config.Env` → anything set with `ENV` is readable by anyone who can inspect or pull the image

```bash
docker run --rm -d --name expose -p 80:80 app5
docker inspect expose        # Path, Args, Entrypoint, Env, PortBindings
docker stop expose           # --rm removes it
```

### Errors I hit

| Symptom | Cause | Fix |
|---|---|---|
| `unknown flag: --rm` | Typed `docker --rm ...`, `--rm` belongs to `docker run` | `docker run --rm ...` |
| `docker run requires at least 1 argument` | Image name missing after `-p 8005:80` | Add the image at the end |
| `No address associated with hostname` | Extra word appended to the `ENTRYPOINT` became a hostname | Pass only the host, not `ping host` |
| `docker ps -a` empty after `run --rm -d` | Main process finished, `--rm` removed the container | Keep a foreground process, or drop `--rm` and read `docker logs` |
| Weird ping output on `CMD` | Markdown link pasted into `CMD` as `[www.google.com](https://...)` | Plain `"www.google.com"` |

!!! tip "Quick revision"

    * `ENTRYPOINT` → what runs, `CMD` → its default arguments
    * `docker run image args` → replaces `CMD`, appended to `ENTRYPOINT`
    * `--entrypoint` → the only way to replace `ENTRYPOINT`
    * Main process ends → container ends

!!! question "Interview points"

    * `CMD` vs `ENTRYPOINT`? → `ENTRYPOINT` is the fixed executable, `CMD` is the default command or arguments and is replaced by anything after the image name in `docker run`
    * Both in one Dockerfile? → `CMD` is passed as arguments to `ENTRYPOINT`, so the image behaves like a command with default flags
    * How do you override `ENTRYPOINT`? → `docker run --entrypoint cmd image`, in Kubernetes the `command` field
    * Why use exec form? → the program is PID 1 and receives `SIGTERM` from `docker stop`, shell form puts `/bin/sh -c` in front and the signal may never reach the app
    * A container starts and exits immediately, why? → its main process finished or ran in the background, keep it in the foreground, for nginx `daemon off;`
    * `docker run app ping host` fails on an image with `ENTRYPOINT ["ping"]`, why? → the extra `ping` is appended as an argument and read as a hostname
    * Where are `ENTRYPOINT` and `CMD` visible? → `docker inspect` shows `Path`, `Args`, `Config.Entrypoint` and `Config.Cmd`
