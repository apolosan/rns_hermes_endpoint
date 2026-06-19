# QUICKSTART — Hermes for Reticulum

**Goal:** run an AI agent on your Reticulum mesh in under 10 minutes.

**Outcome:** any LXMF client — an off-grid [RNode](https://github.com/markqvist/Reticulum) on LoRa, [Sideband](https://github.com/markqvist/Sideband) on your phone, NomadNet, or a custom Python app — can send a message to your bridge and receive a Hermes Agent reply. Mesh clients do not need direct internet. The bridge node (often a VPS or home gateway) holds the uplink to LLM APIs.

**Who this guide is for:** developers and architects who already know Reticulum basics and want the fastest path from zero to a working LXMF endpoint.

## Before you start (5W2H checklist)

| Question | Answer for this guide |
|----------|----------------------|
| **What** are you building? | An LXMF bridge that connects Reticulum mesh traffic to Hermes Agent |
| **Why** now? | To give off-grid nodes AI capability without custom gateway code |
| **Who** sends messages? | Your RNode, Sideband install, or any LXMF peer you allowlist |
| **When** does it run? | As soon as `hermes-reticulum run` starts and Reticulum has mesh paths |
| **Where** does it live? | A Linux/macOS host with Python 3.11+ — VPS, home server, or mesh gateway |
| **How** do you validate success? | A mesh client message reaches the bridge; Hermes reply returns over LXMF |
| **How much** setup? | ~10 minutes, one `.env` file, optional firewall rule on port 37428 |

## Prerequisites

- Linux or macOS with Python **3.11+**
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) installed and responding:

```bash
hermes chat -q "reply with OK only"
```

- (Optional) VPS with port **37428/TCP** open in the firewall, if internet-connected Reticulum peers should reach your bridge

## 1. Clone and install

```bash
git clone https://github.com/apolosan/rns_hermes_endpoint.git
cd rns_hermes_endpoint
bash install.sh
source venv/bin/activate
```

`install.sh` creates the virtual environment, installs the package, prepares `~/.lxmf/storage`, and copies `config/reticulum.conf` to `~/.reticulum/config` when it does not exist yet.

## 2. Configure environment

```bash
cp config/env.example .env
```

Edit `.env` — minimum required fields:

```bash
# Path to hermes, if not on PATH
HERMES_BIN=/path/to/hermes

# LXMF hash of your mesh client (RNode, Sideband, etc.)
HERMES_RETICUM_ALLOW_ALL=false
HERMES_RETICUM_ALLOWED_USERS=YOUR_LXMF_HASH_HERE
```

**Why allowlist?** By default the bridge rejects unknown senders. Add the 32-character hex hash from your RNode identity, Sideband (Settings → Identity), or any client that will talk to the agent.

## 3. Adjust Reticulum (if needed)

File: `~/.reticulum/config` (or `config/reticulum.conf` in the repo as reference).

**TCP Server** — listens for connections on your machine (typical for a VPS bridge):

```ini
[[TCP Server Interface]]
  type = TCPServerInterface
  enabled = yes
  listen_ip = 0.0.0.0
  listen_port = 37428
```

**TCP Client** — connects to an existing mesh peer (optional; links off-grid nodes to internet gateways):

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

On startup, note the **LXMF address** (32-character hex hash). This is the contact address mesh clients use to reach your agent.

Background alternative:

```bash
./start.sh start
./start.sh status
./start.sh stop
```

## 5. Connect from the mesh

Pick the path that matches your deployment.

### Option A — RNode (off-grid, primary use case)

1. Ensure your RNode Reticulum instance has a path to the bridge (LoRa mesh and/or TCP/I2P peers)
2. Send an LXMF message to the bridge hash from your RNode/LXMF tooling
3. The reply routes back over Reticulum — no internet required on the RNode itself

**Success signal:** you receive a Hermes reply on the RNode after one or more mesh hops.

### Option B — Sideband (mobile / desktop)

1. Install [Sideband](https://github.com/markqvist/Sideband/releases/latest)
2. Configure a network interface (TCP to bridge IP:37428, or LoRa)
3. Add the bridge LXMF address as a **contact**
4. Send a test message

**Success signal:** Sideband shows an agent reply within your configured Hermes timeout.

### Option C — Any other LXMF client

Use the same bridge address with NomadNet, custom LXMF scripts, or any Reticulum peer — no Sideband-specific setup required.

## Quick verification

```bash
hermes-reticulum address    # LXMF address to share with mesh clients
hermes-reticulum status     # bridge state
hermes-reticulum run -v     # verbose log for debugging
```

Confirm on the client side that your sender hash appears in `HERMES_RETICUM_ALLOWED_USERS` before testing.

## Common issues

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `hermes: command not found` | Hermes not on PATH | Set `HERMES_BIN` in `.env` |
| Message ignored | Sender not allowlisted | Add client hash to `HERMES_RETICUM_ALLOWED_USERS` |
| Client won't connect | No Reticulum path or blocked port | Check mesh peers, IP, port 37428, firewall, LoRa links |
| LXMF identity error | Corrupted local identity store | Delete `~/.lxmf/storage` **only** if you can regenerate contacts |

## Next steps

- Architecture, security, and full configuration: [README.md](README.md)
- Run as a persistent service: `config/hermes-reticulum*.service`
- Contribute or run tests: `pip install -e ".[dev]" && pytest tests/ -v`

When your first off-grid message gets a reply, you have a production-ready pattern: **mesh transport on the edge, AI reasoning at the gateway.**
