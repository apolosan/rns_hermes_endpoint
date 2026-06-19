# Hermes for Reticulum

**Put an AI agent on your Reticulum mesh — reachable from off-grid RNodes, Sideband, and any LXMF client, without a central messaging server.**

You deploy one bridge node. Field hardware sends encrypted LXMF messages over LoRa, TCP, or I2P. Reticulum routes across hops until Hermes Agent processes the request and the reply travels back the same mesh path. Clients in the field do not need direct internet access.

```
RNode / Sideband / any LXMF client          Hermes bridge (Reticulum node)
┌──────────────────────────┐   LoRa / TCP / I2P   ┌──────────────────────────┐
│  Off-grid mesh client    │ ◄════ Reticulum ═══► │  Hermes for Reticulum    │
│  (no internet required)  │   LXMF (encrypted)   │  └── Hermes Agent (AI)   │
└──────────────────────────┘                      └──────────────────────────┘
         ▲                                                    │
         │         mesh hops through Reticulum peers          │
         └──────── (field nodes, gateways, TCP/I2P bridges) ──┘
```

## Who this is for

| Persona | What you need | What this gives you |
|---------|---------------|---------------------|
| **Mesh developer** | A standard LXMF endpoint you can hit from Python, Sideband, or custom tooling | A drop-in bridge — no proprietary API, no Sideband lock-in |
| **Systems architect** | AI capability at the edge of a heterogeneous mesh (LoRa + TCP + I2P) | One gateway pattern: mesh clients stay off-grid; the bridge holds the uplink to LLM APIs |
| **Field operator** | Reliable comms where cellular and Wi-Fi fail | Ask your agent from an [RNode](https://github.com/markqvist/Reticulum) in the bush; replies route back over the same mesh |

If you design or operate off-grid communication systems, this is the missing link between **Reticulum's transport layer** and **Hermes Agent's reasoning layer**.

## The problem this solves

Off-grid mesh nodes can move data. They usually cannot reach a capable AI without brittle workarounds — custom gateways, ad-hoc HTTP tunnels, or forcing every client to carry its own internet link.

Hermes for Reticulum closes that gap:

- **What:** an LXMF bridge that forwards mesh messages to [Hermes Agent](https://github.com/NousResearch/hermes-agent) and returns replies over [Reticulum](https://reticulum.network).
- **Why:** field nodes should talk to an agent through the mesh they already trust — not through a new protocol stack.
- **Where:** RNodes in remote terrain, event meshes with no ISP, hybrid networks where LoRa peers reach a TCP/I2P gateway.
- **How much effort:** under 10 minutes to a running bridge — see [QUICKSTART.md](QUICKSTART.md).

## What you get

- **AI reachable from off-grid mesh nodes** — especially [RNodes](https://github.com/markqvist/Reticulum) on LoRa; no Android or Sideband required
- **Client-agnostic LXMF** — [Sideband](https://github.com/markqvist/Sideband), NomadNet, custom Python apps, or any Reticulum peer that speaks LXMF
- **Reticulum-native routing** — LoRa, TCP, I2P, and other transports interoperate on one network
- **End-to-end encryption** — Curve25519 key exchange + AES-128; Ed25519 message signatures
- **No central messaging server** — identity-based LXMF delivery across autonomous peers
- **Internet where it belongs** — the bridge node (often a VPS or home gateway) reaches LLM APIs; mesh clients do not need a direct ISP link
- **Access control by LXMF identity hash** — allowlist or blocklist senders before they reach Hermes

## Real-world scenarios

| Scenario | Challenge | Outcome with this bridge |
|----------|-----------|--------------------------|
| **RNode in the field** | No cellular coverage; operator needs situational answers | Message goes out over LoRa; Reticulum forwards through mesh peers; Hermes replies on the return path |
| **Off-grid camp or event** | Local LoRa mesh, no ISP on site | One gateway node with TCP or I2P reachability acts as the AI endpoint for the whole mesh |
| **Hybrid mesh** | Remote nodes on LoRa; infrastructure on TCP | Bridge on a VPS joins both worlds; Hermes uses cloud LLMs while clients stay radio-only |
| **Sideband on a phone** | Mobile operator wants the same agent contact | Same LXMF address — convenient client, not a requirement |

## Quick start

Follow [QUICKSTART.md](QUICKSTART.md) to go from clone to first mesh message in under 10 minutes.

```bash
git clone https://github.com/apolosan/rns_hermes_endpoint.git
cd rns_hermes_endpoint
bash install.sh && source venv/bin/activate
cp config/env.example .env   # set HERMES_BIN and allowed LXMF hashes
hermes-reticulum run           # note the LXMF address printed at startup
```

## Requirements

| Item | Version / detail |
|------|------------------|
| Python | 3.11 or newer |
| Hermes Agent | Installed and working (`hermes chat -q "test"`) |
| Bridge node (optional) | Public IP with TCP port **37428** open, if internet-connected Reticulum peers should reach you |

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
#    Add it as a contact in Sideband, your RNode config, or any LXMF client
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
│  Mesh clients (any LXMF-capable peer)                   │
│  ├── RNode + LoRa radio (primary off-grid use case)     │
│  ├── Sideband (Android / desktop)                       │
│  └── Custom LXMF apps / other Reticulum nodes           │
│       └── Reticulum stack → LoRa / TCP / I2P / …        │
└─────────────────────┬───────────────────────────────────┘
                      │ LXMF messages (encrypted), multi-hop
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Bridge node (VPS, home server, or mesh gateway)        │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Reticulum daemon (TCP :37428, LoRa, I2P, …)    │    │
│  └────────────────────┬────────────────────────────┘    │
│                       ▼                                 │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Hermes for Reticulum (this project)            │    │
│  │  ├── LXMFBridge      — LXMF message handling    │    │
│  │  ├── HermesClient    — hermes CLI subprocess    │    │
│  │  └── AccessControl   — sender filtering         │    │
│  └────────────────────┬────────────────────────────┘    │
│                       ▼                                 │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Hermes Agent (LLM, tools, memory, skills)      │    │
│  │  └── may use internet for model APIs            │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

Reticulum peers interconnect autonomously. An off-grid RNode only needs a path — direct or multi-hop — to the bridge. TCP and I2P interfaces on gateway nodes extend the mesh to internet-connected peers without requiring every client to have an ISP link.

## How it works

1. A mesh client (RNode, Sideband, or any LXMF peer) sends a message to the bridge hash
2. Reticulum routes it across the mesh — LoRa hops, TCP links, I2P tunnels, or a mix
3. LXM Router validates the signature and decrypts the payload
4. A thread pool processes the message in a worker (non-blocking — long Hermes calls do not stall the mesh stack)
5. AccessControl checks the sender against your allowlist
6. HermesClient runs `hermes chat -q "<message>"` (Hermes may use internet on the bridge node)
7. The reply is sent back as an LXMF message to the originating client

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
HERMES_RETICUM_ALLOWED_USERS=your_client_lxmf_hash,optional_second_hash
```

Each client has a 32-character hex LXMF identity hash — from Sideband (Settings → Identity), your RNode/Reticulum identity, or `hermes-reticulum address` on the bridge itself.

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

## Connect from the mesh

Any LXMF client on Reticulum can reach the bridge. Add the bridge's LXMF address (`hermes-reticulum address`) as a contact or destination, then send a plain-text message.

### RNode (recommended for off-grid)

1. Run Reticulum on the RNode with a LoRa interface linked to your mesh
2. Ensure the RNode has a Reticulum path to the bridge (direct LoRa, or via TCP/I2P gateway peers)
3. Send an LXMF message to the bridge hash from your RNode tooling or LXMF client
4. The agent reply routes back over the same mesh

This is the primary scenario: **field hardware with no internet**, talking to an AI through Reticulum hops.

### Sideband (Android / desktop)

1. Install [Sideband](https://github.com/markqvist/Sideband/releases/latest)
2. Configure a network interface (Wi-Fi/TCP or LoRa)
3. Add the bridge's LXMF address as a contact
4. Send a message — the agent replies via Hermes

### Other LXMF clients

NomadNet, custom Python scripts using the [LXMF](https://github.com/markqvist/lxmf) library, or any Reticulum node configured for LXMF delivery can interact with the same bridge address. No Sideband-specific features are required.

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

## Security

- End-to-end encryption (Curve25519 + AES-128)
- Forward secrecy via ephemeral links
- Ed25519 message signatures
- Access control by identity hash
- Thread pool limits concurrent processing
- The LXMF hash is public on the mesh (like a contact identifier)

## Get started

Clone the repo, run the bridge, add your mesh clients to the allowlist, and send your first off-grid message. Step-by-step: [QUICKSTART.md](QUICKSTART.md).

## License

MIT

## Acknowledgments

- [Reticulum](https://reticulum.network) — mesh networking stack (RNode, transports, routing)
- [LXMF](https://github.com/markqvist/lxmf) — messaging protocol
- [Sideband](https://github.com/markqvist/Sideband) — LXMF client (one of many)
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — AI agent
