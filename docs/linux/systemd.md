# systemd & Services

*Hands-on notes, written while building and breaking a custom service*

## What

* Service (daemon) → program running in the background, no window → e.g. `cron`, `cups`, `NetworkManager`, `warp-svc`
* systemd → first program Linux starts at boot (PID 1) → manager of all services
* Job → start services at boot, restart them if they crash, stop them at shutdown, log what happens
* `ps -p 1` → shows systemd as PID 1
* `systemctl` → command to talk to systemd

## See services

* `systemctl list-units --type=service --state=running` → all running services
* `systemctl status cron` → how one service is doing
* Read status → `Loaded:` card found + enabled/disabled | `Active:` running/dead/failed → ignore the rest
* `●` running | `○` stopped | `×` failed
* `Main PID` → process number of the service | `CGroup` → all processes belonging to it
* Bottom lines → journal (systemd's diary for that service)
* `--no-pager` → print fully, no scroll screen | `-l` → don't cut long lines

## Unit file (the card)

* Text file telling systemd how to run a service → ends in `.service`
* `systemctl cat cron` → view a service's card
* `/etc/systemd/system/` → your cards | `/usr/lib/systemd/system/` → package cards, don't edit
* `[Unit]` → what it is → `Description=`
* `[Service]` → how to run it → `ExecStart=/path/to/program` (the exact command systemd runs) | `Restart=on-failure` (restart if it crashes)
* `[Install]` → when to start → `WantedBy=multi-user.target` (normal boot)
* e.g. cups → `ExecStart=/usr/sbin/cupsd -l` → systemd runs that command for you

## Control

* `sudo systemctl start x` → run now
* `sudo systemctl stop x` → kill it now
* `sudo systemctl restart x` → stop + start → new PID
* `sudo systemctl enable x` → start at every boot
* `sudo systemctl disable x` → don't start at boot
* `sudo systemctl enable --now x` → run now + at boot
* `systemctl is-active x` | `is-enabled x` → quick yes/no checks

## start vs enable

* Two separate switches → now (`start`/`stop`) | boot (`enable`/`disable`)
* start only → running now, gone after reboot
* enable only → not running now, starts after reboot
* `disable cups` → `is-enabled` = disabled, `is-active` = active → still running
* `enable` → creates a symlink in `/etc/systemd/system/multi-user.target.wants/` pointing to the card
* `disable` → deletes that symlink, the card stays
* `.wants` folder = boot list → systemd starts everything linked there at boot
* `WantedBy=` in `[Install]` → tells `enable` which boot list → missing = "no installation config" error

## Lab: write your own service

A service that writes the date to a log every 10 seconds.

**1. The script** → `/usr/local/bin/ticker.sh`, then `sudo chmod +x` it

```bash
#!/bin/bash
while true; do
  date >> /tmp/ticker.log
  sleep 10
done
```

**2. The card** → `/etc/systemd/system/ticker.service`

```ini
[Unit]
Description=Ticker: append the date to /tmp/ticker.log every 10s

[Service]
ExecStart=/usr/local/bin/ticker.sh
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

**3. Load and start it**

```bash
sudo systemctl daemon-reload        # re-read cards; needed after every new or edited card
sudo systemctl enable --now ticker  # "Created symlink" = added to the boot list
systemctl status ticker             # active (running)
tail -f /tmp/ticker.log             # new line every 10s
```

## Logs

* `journalctl -u x` → all logs for service x
* `journalctl -u x -n 20 --no-pager` → last 20 lines
* `journalctl -u x -f` → follow live
* `journalctl -p err -b` → all errors since boot
* Don't read every line → look for `failed` / `error` / `No such file`

## Errors I hit

| Symptom | Cause | Fix |
|---|---|---|
| `bad-setting`, "no ExecStart", "no installation config" | `[Unit]` / `[Service]` / `[Install]` headers missing from the card | Add the section headers, `daemon-reload` |
| `× failed` with `status=203/EXEC` | systemd couldn't run `ExecStart`: wrong path (`tickr.sh`, `kicker.sh`) or script not executable | Fix the path, `chmod +x`, `daemon-reload` |
| "Start request repeated too quickly" | `Restart=` retried 5 times and gave up | Fix the cause, `daemon-reload`, `reset-failed x`, `restart x` |
| `status=0/SUCCESS` | Not an error: clean exit | Nothing to fix |

## Debug order

1. `systemctl status x` → Active line + `ExecStart` path + last log lines
2. `journalctl -u x -n 50 --no-pager` → more detail
3. Edited the card? → `daemon-reload` + `restart`
4. Check the `ExecStart` file exists and is executable → `ls -l /path`

!!! question "Interview points"

    * What happens on `systemctl start x` → systemd reads `x.service`, starts dependencies, runs `ExecStart` as a new process, tracks its PID, logs to the journal, and restarts it if `Restart=` is set
    * start vs enable → now vs at boot | `enable` creates a symlink in the `.wants` folder
    * Service won't start after reboot → `is-enabled` (enabled?) → `status` → `journalctl -u` → path/permissions
    * Edited a unit file and nothing changed → forgot `daemon-reload`
