# QUICKSTART — Hermes for Reticulum

Minimal guide to get the bridge running in **under 10 minutes**.

## Prerequisites

- Linux (or macOS) with Python **3.11+**
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) installed and tested:

```bash
hermes chat -q "reply with OK only"
```

- (Optional) VPS with port **37428/TCP** open in the firewall, if the node is reachable from the internet

## 1. Clone and install

```bash
git clone https://github.com/apolosan/rns_hermes_endpoint.git
cd rns_hermes_endpoint
bash install.sh
source venv/bin/activate
```

`install.sh` creates the `venv`, installs the package, prepares `~/.lxmf/storage`, and copies `config/reticulum.conf` to `~/.reticulum/config` when it does not exist yet.

## 2. Configure environment

```bash
cp config/env.example .env
```

Edit `.env` — at minimum:

```bash
# Path to hermes, if not on PATH
HERMES_BIN=/path/to/hermes

# Your Sideband LXMF hash (Sideband → Settings → Identity)
HERMES_RETICUM_ALLOW_ALL=false
HERMES_RETICUM_ALLOWED_USERS=YOUR_LXMF_HASH_HERE
```

## 3. Adjust Reticulum (if needed)

File: `~/.reticulum/config` (or `config/reticulum.conf` in the repo as reference).

**TCP Server** — listens for connections on your machine:

```ini
[[TCP Server Interface]]
  type = TCPServerInterface
  enabled = yes
  listen_ip = 0.0.0.0
  listen_port = 37428
```

**TCP Client** — connects to an existing mesh peer (optional):

```ini
[[TCP Client]]
  type = TCPClientInterface
  enabled = yes
  target_host = YOUR_MESH_PEER_HOST
  target_port = YOUR_MESH_PEER_PORT
```

Firewall (example):

```bash
sudo ufw allow 37428/tcp
```

## 4. Start the bridge

```bash
hermes-reticulum run
```

On startup, note the **LXMF address** (32-character hex hash).

Background alternative:

```bash
./start.sh start
./start.sh status
./start.sh stop
```

## 5. Connect from Sideband

1. Install [Sideband](https://github.com/markqvist/Sideband/releases/latest) on Android
2. Configure a network interface (TCP to server IP:37428, or LoRa)
3. Add the bridge LXMF address as a **contact**
4. Send a test message

## Quick verification

```bash
hermes-reticulum address    # LXMF address
hermes-reticulum status     # bridge state
hermes-reticulum run -v     # verbose log for debugging
```

## Common issues

| Symptom | Fix |
|---------|-----|
| `hermes: command not found` | Set `HERMES_BIN` in `.env` |
| Message ignored | Confirm your hash in `HERMES_RETICUM_ALLOWED_USERS` |
| Sideband won't connect | Check IP, port 37428, and firewall |
| LXMF identity error | Delete `~/.lxmf/storage` **only** if you can regenerate contacts |

## Next steps

- Full details: [README.md](README.md)
- Persistent service: files in `config/hermes-reticulum*.service`
- Development and tests: `pip install -e ".[dev]" && pytest tests/ -v`
