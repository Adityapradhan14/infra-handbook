# Networking

*From The Linux Command Line, chapter 16*

## Basics

* IP address → device's address on a network → e.g. `192.168.1.9/24`
* `/24` (CIDR) → first 24 bits = network → `192.168.1.0–255` is one subnet
* Gateway → router that forwards traffic leaving your subnet → e.g. `192.168.1.1`
* DNS → name to IP → `google.com` → `142.250.x.x`
* Port → which service on a host → 22 SSH, 80 HTTP, 443 HTTPS, 5432 Postgres

## Interfaces + Routes

* `ip a` → all interfaces + IPs (replaces `ifconfig`)
* `lo` → loopback 127.0.0.1 | `eno1` → ethernet | `wlo1` → wifi | `virbr0` → KVM bridge | `CloudflareWARP` → VPN tunnel
* `state UP/DOWN`, `NO-CARRIER` → no cable | `dynamic` → IP from DHCP
* `ip r` → routing table → `default via 192.168.1.1 dev wlo1` = everything else goes to router

## Reachability

* `ping host` → ICMP echo, checks host is up + latency → ttl, time=ms, packet loss
* ping can fail even if host is up → ICMP blocked by firewall/cloud security group
* `traceroute host` → every hop to host (UDP probes by default)
* `* * *` in a hop → hop not replying (blocked/VPN) → try `sudo traceroute -I` (ICMP) or `-T -p 443` (TCP)
* `mtr host` → live ping + traceroute combined

## Ports + Sockets

* `ss -tulpn` → listening ports → `t` tcp, `u` udp, `l` listening, `p` process, `n` numeric
* `ss -tulpn | grep :80` → who is on port 80
* `lsof -i :80` → same, via lsof
* `0.0.0.0:80` → listening on all interfaces | `127.0.0.1:80` → local only, not reachable from outside

## DNS

* `resolvectl query urmilabs.com` → DNS lookup via systemd-resolved
* `dig urmilabs.com +short` → just the IP (`sudo apt install dnsutils`)
* `/etc/hosts` → local name overrides, checked before DNS
* `/etc/resolv.conf` → which DNS server is used

## HTTP Clients

* `curl https://site` → GET, prints body
* `curl -I` → headers only → status code, `server: cloudflare`
* `curl -v` → verbose → DNS, TCP connect, TLS handshake, request/response
* `curl -L` → follow redirects | `-o file` → save to file | `-s` → silent
* `curl -X POST -d 'k=v' url` → send data (APIs, Telegram bot)
* `wget url` → download file | `wget -c` → resume

## SSH

* `ssh user@host` → encrypted remote shell | `ssh -p 2222` → custom port
* `ssh -i ~/.ssh/key user@host` → use specific private key
* `ssh-keygen -t ed25519` → creates `~/.ssh/id_ed25519` (private) + `id_ed25519.pub` (public)
* `ssh-copy-id user@host` → appends pubkey to remote `~/.ssh/authorized_keys`
* Public key → goes on server | Private key → never leaves your machine
* Permissions → `~/.ssh` 700, private key 600, `authorized_keys` 600 → else "Permissions are too open" / key ignored
* `ssh host 'df -h'` → run one command remotely
* `/etc/ssh/sshd_config` → server side → `PasswordAuthentication no`, `PermitRootLogin no` → restart sshd after change
* `~/.ssh/known_hosts` → fingerprints of servers seen → "REMOTE HOST IDENTIFICATION HAS CHANGED" = host key changed → `ssh-keygen -R host`
* `~/.ssh/config` → then just `ssh sshlab`:

```
Host sshlab
    HostName localhost
    Port 2222
    User root
    IdentityFile ~/.ssh/sshlab
```

## File Transfer

* `scp file user@host:/path` → copy to remote | `scp user@host:/path .` → copy from remote | `-r` for dirs
* `sftp user@host` → interactive transfer (`put`, `get`, `ls`)
* `rsync -avz src/ user@host:/dst` → incremental sync, better than scp for big/repeat copies
* `ftp` → plaintext, insecure, skip

!!! question "Interview points"

    * Can't reach a server → `ping` (up?) → `ss` on server (listening?) → firewall/security group → DNS (`resolvectl`/`dig`)
    * App works on server but not from outside → bound to `127.0.0.1` not `0.0.0.0`, or port blocked
    * "Permissions are too open" → `chmod 600` key, `chmod 700 ~/.ssh`
    * Ping fails but curl works → ICMP blocked, host is fine
