#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# install.sh — Install Hermes for Reticulum
# ═══════════════════════════════════════════════════════════════
#
# Usage:
#   bash install.sh              # Install with default settings
#   bash install.sh --venv PATH  # Install into specific venv
#   bash install.sh --global     # Install globally (needs pip --break-system-packages)
#
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/venv"
INSTALL_MODE="venv"

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --venv)
            VENV_DIR="$2"
            INSTALL_MODE="venv"
            shift 2
            ;;
        --global)
            INSTALL_MODE="global"
            shift
            ;;
        --help|-h)
            echo "Usage: bash install.sh [--venv DIR] [--global]"
            echo "  --venv DIR   Install into a virtual environment (default: ./venv)"
            echo "  --global     Install globally (needs --break-system-packages or pipx)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "═══ Hermes for Reticulum — Installer ═══"
echo ""

# ─── Check Python version ───
PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3; do
    if command -v "$candidate" &>/dev/null; then
        version=$("$candidate" --version 2>&1 | grep -oP '\d+\.\d+')
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [[ "$major" -ge 3 && "$minor" -ge 11 ]]; then
            PYTHON="$candidate"
            echo "✓ Found Python $version ($candidate)"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    echo "✗ Python 3.11+ required but not found"
    exit 1
fi

# ─── Install ───
if [[ "$INSTALL_MODE" == "venv" ]]; then
    echo ""
    echo "Installing into virtual environment: $VENV_DIR"

    if [[ ! -d "$VENV_DIR" ]]; then
        "$PYTHON" -m venv "$VENV_DIR"
        echo "  Created venv"
    fi

    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip setuptools wheel
    pip install -e "$SCRIPT_DIR"

    echo ""
    echo "✓ Installed into $VENV_DIR"
    echo ""
    echo "  To use:"
    echo "    source $VENV_DIR/bin/activate"
    echo "    hermes-reticulum --help"

else
    echo ""
    echo "Installing globally..."
    pip install --break-system-packages -e "$SCRIPT_DIR"
    echo ""
    echo "✓ Installed globally"
    echo "  Run: hermes-reticulum --help"
fi

# ─── Create config directories ───
echo ""
echo "Setting up configuration..."

RETICULUM_DIR="${HOME}/.reticulum"
LXMF_DIR="${HOME}/.lxmf/storage"

if [[ ! -d "$RETICULUM_DIR" ]]; then
    mkdir -p "$RETICULUM_DIR"
    # Copy example config if not present
    if [[ ! -f "$RETICULUM_DIR/config" && -f "$SCRIPT_DIR/config/reticulum.conf" ]]; then
        cp "$SCRIPT_DIR/config/reticulum.conf" "$RETICULUM_DIR/config"
        echo "  ✓ Created Reticulum config at $RETICULUM_DIR/config"
    fi
else
    echo "  ✓ Reticulum config directory exists"
fi

mkdir -p "$LXMF_DIR"
echo "  ✓ LXMF storage directory ready"

# ─── Copy env file if not present ───
ENV_FILE="${SCRIPT_DIR}/.env"
if [[ ! -f "$ENV_FILE" && -f "$SCRIPT_DIR/config/env.example" ]]; then
    cp "$SCRIPT_DIR/config/env.example" "$ENV_FILE"
    echo "  ✓ Created .env from template"
    echo "    → Edit $ENV_FILE to customize"
fi

# ─── Done ───
echo ""
echo "═══ Installation complete! ═══"
echo ""
echo "Next steps:"
echo "  1. Review and edit .env for your setup"
echo "  2. Start the bridge:  hermes-reticulum run"
echo "  3. Note the LXMF address printed on startup"
echo "  4. Add this address as a contact in Sideband (Android)"
echo ""
echo "For Hermes gateway integration:"
echo "  1. Copy plugin/ to ~/.hermes/plugins/reticulum/"
echo "  2. Restart the Hermes gateway"
echo "  3. Run 'hermes gateway status' to verify"
echo ""
