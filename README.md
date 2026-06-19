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

## Quick Start

### Prerequisites

- Python 3.11+
- Hermes Agent installed (`curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash`)

### Install

```bash
git clone https://github.com/einarsantos/rns_hermes_endpoint.git
cd rns_hermes_endpoint
bash install.sh
```

### Configure

```bash
# Edit the environment file
nano .env

# Set your display name (shown in Sideband)
RETICULUM_DISPLAY_NAME="Hermes for Reticulum"
```

### Run

```bash
# Start the bridge
source venv/bin/activate
hermes-reticulum run

# Or with verbose logging
hermes-reticulum run --verbose
```

On first run, the bridge will:
1. Generate an Ed25519 identity (saved to `~/.lxmf/storage/`)
2. Start listening for LXMF messages
3. Announce its address on the Reticulum network
4. Print the **LXMF address** — add this in Sideband as a contact

### Connect from Sideband (Android)

1. Install [Sideband](https://github.com/markqvist/Sideband/releases/latest)
2. Configure a network interface (Wi-Fi/TCP or LoRa)
3. Add the bridge's LXMF address as a contact
4. Send a message — the AI agent will reply!

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

## Commands

```bash
# Start the bridge (default)
hermes-reticulum run

# Show LXMF address
hermes-reticulum address

# Show bridge status
hermes-reticulum status

# Start with custom options
hermes-reticulum run \
  --display-name "My AI" \
  --stamp-cost 4 \
  --timeout 120 \
  --verbose
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RETICULUM_DISPLAY_NAME` | `Hermes for Reticulum` | Name shown in Sideband |
| `RETICULUM_STORAGE` | `~/.lxmf/storage` | Message/identity storage path |
| `RETICULUM_STAMP_COST` | `8` | LXMF stamp cost (bandwidth throttle) |
| `RETICULUM_CONFIG` | `~/.reticulum` | Reticulum config directory |
| `HERMES_BIN` | `hermes` | Path to hermes CLI |
| `HERMES_TIMEOUT` | `300` | Hermes processing timeout (seconds) |
| `HERMES_RETICUM_ALLOW_ALL` | `true` | Allow all senders |
| `HERMES_RETICUM_ALLOWED_USERS` | (empty) | Allowlist of LXMF hashes |
| `HERMES_RETICUM_BLOCKED_USERS` | (empty) | Blocklist of LXMF hashes |

### Reticulum Config

The Reticulum config is at `~/.reticulum/config`. A template is included in `config/reticulum.conf`.

**For VPS (TCP server):**
```ini
[interfaces]
  [[TCP Server]]
    type = TCPServerInterface
    listen_ip = 0.0.0.0
    listen_port = 37428
```

**For LoRa (when hardware is available):**
```ini
[interfaces]
  [[LoRa Interface]]
    type = LoRaInterface
    port = /dev/ttyUSB0
    speed = 115200
    spreading_factor = 10
    bandwidth = 125000
```

### Access Control

By default, anyone on the Reticulum network can message the agent (`HERMES_RETICUM_ALLOW_ALL=true`).

To restrict access:

```bash
# In .env
HERMES_RETICUM_ALLOW_ALL=false
HERMES_RETICUM_ALLOWED_USERS=aabbccdd11223344aabbccdd11223344
```

Find your Sideband LXMF hash in Sideband → Settings → Identity.

## Hermes Gateway Integration

For deeper integration with the Hermes gateway (as a native platform alongside Telegram, Discord, etc.):

```bash
# Copy the plugin
cp -r src/hermes_reticulum/plugin ~/.hermes/plugins/reticulum

# Restart the gateway
hermes gateway restart

# Verify
hermes gateway status
```

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
pytest

# Lint
ruff check src/ tests/
```

## LoRa Setup (Future)

When LoRa hardware is available:

1. Connect SX1276/SX1262 module to the VPS (USB)
2. Update `~/.reticulum/config` with LoRa interface
3. Ensure the LoRa radio parameters match your Sideband configuration
4. The bridge works identically — Reticulum handles the transport layer

**Recommended hardware:**
- Heltec WiFi LoRa 32 V3
- LILYGO T3S3 LoRa
- Adafruit RFM95W Breakout

## How It Works

1. **Sideband** sends an LXMF message addressed to the bridge's LXMF hash
2. **Reticulum** routes the message (over LoRa, TCP, or I2P)
3. **LXM Router** decrypts and validates the message signature
4. **AccessControl** checks if the sender is allowed
5. **HermesClient** calls `hermes chat -q "<message>"` 
6. **Hermes Agent** processes the message (LLM, tools, memory, etc.)
7. **LXMFBridge** sends the reply back as an LXMF message
8. **Sideband** receives the reply

## Security

- ✅ End-to-end encryption (Curve25519 + AES-128)
- ✅ Forward Secrecy via ephemeral links
- ✅ Ed25519 message signatures
- ✅ No central server required
- ✅ Access control by identity hash
- ⚠️ LXMF hash is public (like a phone number)

## License

MIT

## Acknowledgments

- [Reticulum](https://reticulum.network) by Mark Qvist — the networking stack
- [LXMF](https://github.com/markqvist/lxmf) — the messaging protocol
- [Sideband](https://github.com/markqvist/Sideband) — the Android client
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous Research — the AI agent
