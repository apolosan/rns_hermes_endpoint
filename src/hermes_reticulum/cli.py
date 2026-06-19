#!/usr/bin/env python3
"""
CLI entry point for Hermes for Reticulum.

Usage:
    hermes-reticulum              # Start the bridge (default)
    hermes-reticulum --announce   # Start and announce
    hermes-reticulum --status     # Show bridge status
    hermes-reticulum --address    # Print the LXMF address only
"""

import argparse
import logging
import os
import sys

from hermes_reticulum import __version__
from hermes_reticulum.core.acl import AccessControl
from hermes_reticulum.core.bridge import LXMFBridge
from hermes_reticulum.core.hermes_client import HermesClient


def setup_logging(verbose: bool = False):
    """Configure logging for the bridge."""
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(level=level, format=fmt, datefmt="%Y-%m-%d %H:%M:%S")


def cmd_run(args):
    """Start the bridge and run until interrupted."""
    setup_logging(args.verbose)
    logger = logging.getLogger("hermes_reticulum.cli")

    # Build configuration from env / args
    display_name = args.display_name or os.getenv("RETICULUM_DISPLAY_NAME", "Hermes for Reticulum")
    storage = args.storage or os.getenv("RETICULUM_STORAGE", None)
    stamp_cost = args.stamp_cost or int(os.getenv("RETICULUM_STAMP_COST", "8"))
    rns_config = args.rns_config or os.getenv("RETICULUM_CONFIG", None)
    hermes_bin = args.hermes_bin or os.getenv("HERMES_BIN", "hermes")
    timeout = args.timeout or int(os.getenv("HERMES_TIMEOUT", "300"))

    # Initialize components
    acl = AccessControl()
    hermes = HermesClient(hermes_bin=hermes_bin, timeout=timeout)
    bridge = LXMFBridge(
        display_name=display_name,
        storage_path=storage,
        stamp_cost=stamp_cost,
        rns_config_path=rns_config,
    )

    # Wire up: LXMF message → ACL check → Hermes → reply
    def handle_message(source_hash: str, content: str) -> str | None:
        if not acl.is_allowed(source_hash):
            logger.info("Message from %s rejected by ACL", source_hash[:16])
            return "⛔ Acesso não autorizado."
        return hermes.chat(content)

    bridge.set_message_handler(handle_message)

    # Start
    logger.info("Display name: %s", display_name)
    logger.info("ACL mode: %s", acl.mode)
    logger.info("Hermes binary: %s", hermes_bin)
    logger.info("Timeout: %ds", timeout)

    bridge.run_forever()


def cmd_address(args):
    """Print the LXMF address of an existing identity."""
    setup_logging(False)

    storage = args.storage or os.getenv("RETICULUM_STORAGE", os.path.expanduser("~/.lxmf/storage"))
    identity_path = os.path.join(storage, "hermes_identity")

    import RNS

    if not os.path.exists(identity_path):
        print(f"No identity found at {identity_path}")
        print("Run 'hermes-reticulum' first to generate one.")
        sys.exit(1)

    RNS.Reticulum()  # init
    identity = RNS.Identity.from_file(identity_path)
    print(f"LXMF Address: {RNS.prettyhexrep(identity.hash)}")


def cmd_status(args):
    """Show bridge status."""
    setup_logging(False)

    storage = args.storage or os.getenv("RETICULUM_STORAGE", os.path.expanduser("~/.lxmf/storage"))
    identity_path = os.path.join(storage, "hermes_identity")
    acl = AccessControl()

    print("═══ Hermes for Reticulum ═══")
    print(f"  Version:   {__version__}")
    print(f"  Storage:   {storage}")
    print(f"  Identity:  {'found' if os.path.exists(identity_path) else 'not created yet'}")
    print(f"  ACL mode:  {acl.mode}")
    print()

    if os.path.exists(identity_path):
        import RNS
        RNS.Reticulum()
        identity = RNS.Identity.from_file(identity_path)
        print(f"  Address:   {RNS.prettyhexrep(identity.hash)}")

        # Show RNS interfaces
        print()
        print("  RNS Interfaces:")
        try:
            rns = RNS.Reticulum()
            for iface in rns.interfaces:
                print(f"    - {iface}")
        except Exception:
            print("    (unable to list interfaces)")
    else:
        print("  Run 'hermes-reticulum' to initialize.")


def main():
    parser = argparse.ArgumentParser(
        prog="hermes-reticulum",
        description="Hermes for Reticulum — AI agent on the mesh network",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", help="Command to run")

    # Default: run
    run_p = sub.add_parser("run", help="Start the bridge (default)")
    run_p.add_argument("--display-name", "-n", help="Display name on the mesh")
    run_p.add_argument("--storage", "-s", help="Storage path for identity/messages")
    run_p.add_argument("--stamp-cost", type=int, help="LXMF stamp cost")
    run_p.add_argument("--rns-config", help="Path to Reticulum config dir")
    run_p.add_argument("--hermes-bin", help="Path to hermes CLI binary")
    run_p.add_argument("--timeout", type=int, help="Hermes timeout in seconds")
    run_p.add_argument("--verbose", "-v", action="store_true", help="Debug logging")
    run_p.set_defaults(func=cmd_run)

    # Address
    addr_p = sub.add_parser("address", help="Show LXMF address")
    addr_p.add_argument("--storage", "-s", help="Storage path")
    addr_p.set_defaults(func=cmd_address)

    # Status
    stat_p = sub.add_parser("status", help="Show bridge status")
    stat_p.add_argument("--storage", "-s", help="Storage path")
    stat_p.set_defaults(func=cmd_status)

    # Parse — if no subcommand, default to run
    args = parser.parse_args()
    if args.command is None:
        # Default: run with global flags
        args = parser.parse_args(["run"] + sys.argv[1:])
        # Re-parse with run-specific args
        run_parser = sub.choices["run"]
        args = run_parser.parse_args(sys.argv[1:])
        args.func = cmd_run

    args.func(args)


if __name__ == "__main__":
    main()
