# Hermes for Reticulum

🛜 **AI agent on the mesh network** — Chat with [Hermes Agent](https://github.com/NousResearch/hermes-agent) via [Sideband](https://github.com/markqvist/Sideband) over [Reticulum](https://reticulum.network), even off-grid over LoRa.

```
Sideband (Android)                    Hermes Agent (VPS)
┌──────────────┐    LoRa / TCP / I2P   ┌──────────────────┐
│  💬 Message  │ ◄══════ Reticulum ═══► │  🤖 AI Agent     │
│              │    LXMF (encrypted)    │                  │
└──────────────┘                        └──────────────────┘
```

## What is this?

Hermes for Reticulum is a bridge that connects the Hermes AI agent framework to the Reticulum mesh networking stack via the LXMF messaging protocol. This allows you to:

- **Chat with your AI agent from anywhere** — even without internet, using LoRa radio
- **End-to-end encryption** by default (Curve25519 + AES-128)
- **Zero infrastructure** — no servers, no accounts, no sign-ups
- **Works with Sideband** on Android, Linux, macOS, and Windows

## Requirements

- Python 3.11+
- Hermes Agent installed and working (`hermes chat -q "test"`)
- VPS with a public IP and port 37428 open (TCP)

## Quick Install

```bash
# 1. Clone the repository
git clone https://github.com/einarsantos/rns_hermes_endpoint.git
cd rns_hermes_endpoint

# 2. Run the installer (creates venv and installs)
bash install.sh

# 3. Activate the venv
source venv/bin/activate

# 4. Configure Reticulum with TCP server interface
#    Edit ~/.reticulum/config and add under [interfaces]:
#
#    [[TCP Server]]
#      type = TCPServerInterface
#      listen_ip = 0.0.0.0
#      listen_port = 37428
#      enabled = Yes

# 5. Open port 37428 in your firewall
#    ufw allow 37428/tcp
#    # or
#    iptables -A INPUT -p tcp --dport 37428 -j ACCEPT

# 6. Start the bridge
hermes-reticulum run

# 7. Note the LXMF address printed on startup
#    Add this address as a contact in Sideband
```

## Verified Working

All components have been tested and verified:

| Component | Status | Test |
|-----------|--------|------|
| RNS + LXMF | ✅ | RNS 1.3.5, LXMF 1.0.1 |
| TCP Server | ✅ | Port 37428 listening |
| Identity | ✅ | Generated + persisted (64 bytes) |
| Hermes CLI | ✅ | Auto-detected at `/opt/hermes/.venv/bin/hermes` |
| Subprocess call | ✅ | `hermes chat -q` returns reply |
| Thread pool | ✅ | 4 workers, non-blocking |
| ACL | ✅ | Open / allowlist / blocklist modes |
| CLI | ✅ | `run`, `status`, `address` commands |
| Systemd | ✅ | Service file ready (user-level) |
| Lint | ✅ | ruff: 0 errors |
| Tests | ✅ | 12/12 passing |

## Commands

```bash
# Start the bridge (default)
hermes-reticulum run

# Start with verbose logging
hermes-reticulum run --verbose

# Show LXMF address
hermes-reticulum address

# Show bridge status
hermes-reticulum status

# Start with custom options
hermes-reticulum run \
  --display-name "My AI" \
  --stamp-cost 4 \
  --timeout 120 \
  --hermes-bin /path/to/hermes
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Sideband (Android / Linux)                             │
│  └── LXMF Client                                        │
│       └── Reticulum Stack                               │
│            └── LoRa / TCP / I2P Interface               │
└─────────────────────┬───────────────────────────────────┘
                      │ LXMF messages (encrypted)
                      ▼
┌─────────────────────────────────────────────────────────┐
│  VPS / Server                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Reticulum Daemon (rns)                         │    │
│  │  └── TCP Server Interface (port 37428)          │    │
│  └────────────────────┬────────────────────────────┘    │
│                       ▼                                  │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Hermes for Reticulum (this project)            │    │
│  │  ├── LXMFBridge     — LXMF message handling     │    │
│  │  │   └── ThreadPool  — non-blocking handlers     │    │
│  │  ├── HermesClient   — calls hermes CLI           │    │
│  │  └── AccessControl  — sender filtering           │    │
│  └────────────────────┬────────────────────────────┘    │
│                       ▼                                  │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Hermes Agent                                    │    │
│  │  └── LLM + Tools + Memory + Skills              │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RETICULUM_DISPLAY_NAME` | `Hermes for Reticulum` | Name shown in Sideband |
| `RETICULUM_STORAGE` | `~/.lxmf/storage` | Message/identity storage path |
| `RETICULUM_STAMP_COST` | `8` | LXMF stamp cost (bandwidth throttle) |
| `RETICULUM_CONFIG` | `~/.reticulum` | Reticulum config directory |
| `HERMES_BIN` | *(auto-detected)* | Path to hermes CLI |
| `HERMES_TIMEOUT` | `300` | Hermes processing timeout (seconds) |
| `HERMES_RETICUM_ALLOW_ALL` | `true` | Allow all senders |
| `HERMES_RETICUM_ALLOWED_USERS` | *(empty)* | Allowlist of LXMF hashes |
| `HERMES_RETICUM_BLOCKED_USERS` | *(empty)* | Blocklist of LXMF hashes |

### Hermes Binary Detection

The bridge auto-detects the `hermes` binary in this order:
1. `hermes` in PATH
2. `/opt/hermes/.venv/bin/hermes`
3. `/opt/hermes/bin/hermes`
4. `~/.hermes/bin/hermes`
5. `~/.local/bin/hermes`

Override with `--hermes-bin` or `HERMES_BIN` env var.

### Access Control

By default, anyone on the Reticulum network can message the agent (`HERMES_RETICUM_ALLOW_ALL=true`).

To restrict access:

```bash
# In .env
HERMES_RETICUM_ALLOW_ALL=false
HERMES_RETICUM_ALLOWED_USERS=aabbccdd11223344aabbccdd11223344
```

Find your Sideband LXMF hash in Sideband → Settings → Identity.

## Systemd Service

### User-level (no root)

```bash
# Install
mkdir -p ~/.config/systemd/user/
cp config/hermes-reticulum.user.service ~/.config/systemd/user/hermes-reticulum.service
systemctl --user daemon-reload
systemctl --user enable hermes-reticulum
systemctl --user start hermes-reticulum

# Status
systemctl --user status hermes-reticulum

# Logs
journalctl --user -u hermes-reticulum -f
```

### System-level (root)

```bash
# Install
sudo cp config/hermes-reticulum.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable hermes-reticulum
sudo systemctl start hermes-reticulum
```

## Connect from Sideband (Android)

1. Install [Sideband](https://github.com/markqvist/Sideband/releases/latest)
2. Configure a network interface (Wi-Fi/TCP or LoRa)
3. Add the bridge's LXMF address as a contact
4. Send a message — the AI agent will reply!

## Development

```bash
# Clone
git clone https://github.com/einarsantos/rns_hermes_endpoint.git
cd rns_hermes_endpoint

# Install in dev mode
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Lint
ruff check src/ tests/
```

## How It Works

1. **Sideband** sends an LXMF message addressed to the bridge's LXMF hash
2. **Reticulum** routes the message (over LoRa, TCP, or I2P)
3. **LXM Router** decrypts and validates the message signature
4. **ThreadPool** dispatches to a worker (non-blocking)
5. **AccessControl** checks if the sender is allowed
6. **HermesClient** calls `hermes chat -q "<message>"`
7. **Hermes Agent** processes the message (LLM, tools, memory, etc.)
8. **LXMFBridge** sends the reply back as an LXMF message
9. **Sideband** receives the reply

## Security

- ✅ End-to-end encryption (Curve25519 + AES-128)
- ✅ Forward Secrecy via ephemeral links
- ✅ Ed25519 message signatures
- ✅ No central server required
- ✅ Access control by identity hash
- ✅ Thread pool limits concurrent processing
- ⚠️ LXMF hash is public (like a phone number)

## License

MIT

## Acknowledgments

- [Reticulum](https://reticulum.network) by Mark Qvist — the networking stack
- [LXMF](https://github.com/markqvist/lxmf) — the messaging protocol
- [Sideband](https://github.com/markqvist/Sideband) — the Android client
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous Research — the AI agent
