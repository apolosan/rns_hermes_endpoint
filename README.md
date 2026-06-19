# Hermes for Reticulum

Bridge between [Hermes Agent](https://github.com/NousResearch/hermes-agent) and the [Reticulum](https://reticulum.network) mesh network via [LXMF](https://github.com/markqvist/lxmf). Chat with your AI agent through [Sideband](https://github.com/markqvist/Sideband) — even off-grid over LoRa.

```
Sideband (Android)                    Hermes Agent (server)
┌──────────────┐    LoRa / TCP / I2P   ┌──────────────────┐
│  Message     │ ◄══════ Reticulum ═══► │  AI Agent        │
│              │    LXMF (encrypted)    │                  │
└──────────────┘                        └──────────────────┘
```

## What is this?

This project implements an LXMF bridge that forwards messages from the Reticulum network to Hermes Agent and sends replies back. Key benefits:

- **Chat with AI from anywhere** — even without internet, using LoRa radio
- **End-to-end encryption** (Curve25519 + AES-128)
- **No central infrastructure** — no proprietary servers or sign-ups
- **Sideband compatible** (Android, Linux, macOS, Windows)

## Requirements

| Item | Version / detail |
|------|------------------|
| Python | 3.11 or newer |
| Hermes Agent | Installed and working (`hermes chat -q "test"`) |
| Server (optional) | Public IP with an open TCP port (default: 37428) |

## Quick start

To get running in a few minutes, follow [QUICKSTART.md](QUICKSTART.md).

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/apolosan/rns_hermes_endpoint.git
cd rns_hermes_endpoint

# 2. Install (creates venv and dependencies)
bash install.sh

# 3. Activate the virtual environment
source venv/bin/activate

# 4. Configure environment variables
cp config/env.example .env
# Edit .env for your deployment

# 5. Configure Reticulum (TCP Server interface)
#    The installer copies config/reticulum.conf to ~/.reticulum/config if missing.
#    Adjust listen_port and, if needed, the TCP Client peer:
#
#    [[TCP Server Interface]]
#      type = TCPServerInterface
#      listen_ip = 0.0.0.0
#      listen_port = 37428
#
#    [[TCP Client]]
#      target_host = YOUR_MESH_PEER_HOST
#      target_port = YOUR_MESH_PEER_PORT

# 6. Open the firewall port (if exposing the node to the internet)
sudo ufw allow 37428/tcp

# 7. Start the bridge
hermes-reticulum run

# 8. Note the LXMF address printed at startup
#    Add it as a contact in Sideband
```

## Commands

```bash
hermes-reticulum run              # Start the bridge
hermes-reticulum run --verbose    # Verbose logging
hermes-reticulum address          # Show LXMF address
hermes-reticulum status           # Bridge status

# Custom options
hermes-reticulum run \
  --display-name "My Agent" \
  --stamp-cost 4 \
  --timeout 120 \
  --hermes-bin /path/to/hermes
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Sideband (Android / Linux)                             │
│  └── LXMF Client → Reticulum Stack → LoRa/TCP/I2P       │
└─────────────────────┬───────────────────────────────────┘
                      │ LXMF messages (encrypted)
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Server / VPS                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Reticulum daemon (TCP interface :37428)        │    │
│  └────────────────────┬────────────────────────────┘    │
│                       ▼                                  │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Hermes for Reticulum (this project)            │    │
│  │  ├── LXMFBridge      — LXMF message handling    │    │
│  │  ├── HermesClient    — hermes CLI subprocess    │    │
│  │  └── AccessControl   — sender filtering         │    │
│  └────────────────────┬────────────────────────────┘    │
│                       ▼                                  │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Hermes Agent (LLM, tools, memory, skills)      │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Configuration

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RETICULUM_DISPLAY_NAME` | `Hermes for Reticulum` | Name shown on the mesh |
| `RETICULUM_STORAGE` | `~/.lxmf/storage` | LXMF storage path |
| `RETICULUM_STAMP_COST` | `8` | Stamp cost (bandwidth throttle) |
| `RETICULUM_CONFIG` | `~/.reticulum` | Reticulum config directory |
| `HERMES_BIN` | *(auto-detected)* | Path to the `hermes` binary |
| `HERMES_TIMEOUT` | `300` | Hermes timeout (seconds) |
| `HERMES_RETICUM_ALLOW_ALL` | `false` | Allow any sender |
| `HERMES_RETICUM_ALLOWED_USERS` | *(empty)* | LXMF hash allowlist |
| `HERMES_RETICUM_BLOCKED_USERS` | *(empty)* | LXMF hash blocklist |

Full template: [config/env.example](config/env.example).

### Hermes binary detection

Automatic search order:

1. `hermes` on `PATH`
2. `/opt/hermes/.venv/bin/hermes`
3. `/opt/hermes/bin/hermes`
4. `~/.hermes/bin/hermes`
5. `~/.local/bin/hermes`

Override with `--hermes-bin` or the `HERMES_BIN` variable.

### Access control

By default, only allowlisted addresses can interact (`HERMES_RETICUM_ALLOW_ALL=false`).

```bash
# In .env
HERMES_RETICUM_ALLOW_ALL=false
HERMES_RETICUM_ALLOWED_USERS=your_sideband_lxmf_hash,optional_second_hash
```

Your LXMF hash is shown in Sideband → Settings → Identity.

## Systemd service

Adjust paths in `config/hermes-reticulum*.service` before installing.

### User-level (no root)

```bash
mkdir -p ~/.config/systemd/user/
cp config/hermes-reticulum.user.service ~/.config/systemd/user/hermes-reticulum.service
# Edit WorkingDirectory, Environment, and ExecStart for your paths
systemctl --user daemon-reload
systemctl --user enable --now hermes-reticulum
journalctl --user -u hermes-reticulum -f
```

### System-level (root)

```bash
sudo cp config/hermes-reticulum.service /etc/systemd/system/
# Edit paths and service user for your deployment
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-reticulum
```

## Connect from Sideband (Android)

1. Install [Sideband](https://github.com/markqvist/Sideband/releases/latest)
2. Configure a network interface (Wi-Fi/TCP or LoRa)
3. Add the bridge's LXMF address as a contact
4. Send a message — the agent replies via Hermes

## Development

```bash
git clone https://github.com/apolosan/rns_hermes_endpoint.git
cd rns_hermes_endpoint

python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

python -m pytest tests/ -v
ruff check src/ tests/
```

## How it works

1. Sideband sends an LXMF message to the bridge hash
2. Reticulum routes it (LoRa, TCP, or I2P)
3. LXM Router validates the signature and decrypts the payload
4. A thread pool processes the message in a worker (non-blocking)
5. AccessControl checks the sender
6. HermesClient runs `hermes chat -q "<message>"`
7. The reply is sent back as an LXMF message to Sideband

## Security

- End-to-end encryption (Curve25519 + AES-128)
- Forward secrecy via ephemeral links
- Ed25519 message signatures
- Access control by identity hash
- Thread pool limits concurrent processing
- The LXMF hash is public on the mesh (like a contact identifier)

## License

MIT

## Acknowledgments

- [Reticulum](https://reticulum.network) — mesh networking stack
- [LXMF](https://github.com/markqvist/lxmf) — messaging protocol
- [Sideband](https://github.com/markqvist/Sideband) — mobile client
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — AI agent
