"""
LXMF Message Bridge — the core engine that connects Reticulum/LXMF to Hermes Agent.

Manages the LXM Router, receives messages from Sideband users,
dispatches them to Hermes, and sends replies back over the mesh.

Thread safety: The LXMF delivery callback runs inside the RNS event loop
thread. To avoid blocking the mesh stack, we dispatch message handling to
a separate thread pool so that long-running operations (like calling the
Hermes CLI) don't stall incoming message processing.
"""

import logging
import os
import signal
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import LXMF
import RNS

from hermes_reticulum.core.adapter import prepare_reply
from hermes_reticulum.core.profiler import ChannelMetrics, ChannelProfiler

logger = logging.getLogger("hermes_reticulum.bridge")

# Max concurrent message handlers — prevents hermes subprocess flood
_MAX_HANDLERS = 4


class LXMFBridge:
    """
    Bridges LXMF messages to/from Hermes Agent.

    This class owns the RNS instance, the LXM Router, and the identity.
    It receives incoming LXMF messages, invokes a configurable handler
    (which can call Hermes via CLI, API, or direct import), and sends
    replies back over the same LXMF channel.
    """

    def __init__(
        self,
        display_name: str = "Hermes for Reticulum",
        storage_path: str | Path | None = None,
        stamp_cost: int = 8,
        enforce_stamps: bool = False,
        rns_config_path: str | Path | None = None,
    ):
        """
        Initialize the LXMF bridge.

        Args:
            display_name: Human-readable name announced on the mesh.
            storage_path: Where to persist LXMF messages and identity.
            stamp_cost: LXMF stamp cost (bandwidth throttle).
            enforce_stamps: Whether to require valid stamps from senders.
            rns_config_path: Path to Reticulum config directory (None = default).
        """
        self.display_name = display_name
        self.storage_path = Path(storage_path or os.path.expanduser("~/.lxmf/storage"))
        self.stamp_cost = stamp_cost
        self.enforce_stamps = enforce_stamps
        self.rns_config_path = str(rns_config_path) if rns_config_path else None

        # Will be set during start()
        self.reticulum: RNS.Reticulum | None = None
        self.router: LXMF.LXMRouter | None = None
        self.identity: RNS.Identity | None = None
        self.destination: RNS.Destination | None = None

        # Message handler: called with (source_hash, content, profile)
        self._message_handler = None
        self._running = False

        # Channel profiler for adaptive responses
        self.profiler = ChannelProfiler()

        # Thread pool for non-blocking message processing
        self._pool: ThreadPoolExecutor | None = None

    @property
    def address(self) -> str | None:
        """The LXMF address (hex hash) of this bridge, or None if not started."""
        if self.destination:
            return RNS.prettyhexrep(self.destination.hash)
        return None

    def set_message_handler(self, handler):
        """
        Register the handler called for each incoming message.

        The handler receives (source_hash_hex, message_content) and should
        return a reply string (or None for no reply).
        """
        self._message_handler = handler

    def start(self):
        """
        Initialize RNS, create the LXM Router, register identity,
        and start listening for messages.
        """
        logger.info("Starting Hermes for Reticulum bridge...")

        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Initialize Reticulum
        self.reticulum = RNS.Reticulum(self.rns_config_path)
        logger.info("Reticulum initialized")

        # Create LXM Router
        self.router = LXMF.LXMRouter(
            storagepath=str(self.storage_path),
            enforce_stamps=self.enforce_stamps,
        )

        # Load or create identity
        identity_path = self.storage_path / "hermes_identity"
        if identity_path.exists():
            self.identity = RNS.Identity.from_file(str(identity_path))
            if self.identity is None:
                logger.warning("Corrupt identity at %s, creating new one", identity_path)
                self.identity = RNS.Identity()
                self.identity.to_file(str(identity_path))
            else:
                logger.info("Loaded existing identity from %s", identity_path)
        else:
            self.identity = RNS.Identity()
            self.identity.to_file(str(identity_path))
            logger.info("Created new identity at %s", identity_path)

        # Register delivery identity and destination
        self.destination = self.router.register_delivery_identity(
            self.identity,
            display_name=self.display_name,
            stamp_cost=self.stamp_cost,
        )

        # Register the inbound message callback
        self.router.register_delivery_callback(self._on_lxmf_message)

        # Create thread pool for message processing
        self._pool = ThreadPoolExecutor(
            max_workers=_MAX_HANDLERS,
            thread_name_prefix="lxmf-handler",
        )

        self._running = True

        logger.info(
            "Bridge ready — LXMF address: %s | Display name: %s",
            self.address,
            self.display_name,
        )

    def announce(self):
        """Announce our destination on the Reticulum network."""
        if self.destination:
            self.destination.announce()
            logger.info("Announced destination %s", self.address)

    def _on_lxmf_message(self, message):
        """
        Internal callback for incoming LXMF messages.

        This runs inside the RNS event loop thread. To avoid blocking
        the mesh stack, we dispatch the actual processing to a thread pool.
        """
        try:
            # Extract message content (fast, safe to do here)
            if hasattr(message, "content_as_string"):
                content = message.content_as_string()
            else:
                content = str(message.content)

            source_hash = RNS.prettyhexrep(message.source_hash)
            src_bytes = message.source_hash
            source_hash_raw = (
                src_bytes.hex() if isinstance(src_bytes, bytes) else src_bytes.hex()
            )

            # Log reception
            sig = "valid" if message.signature_validated else "invalid/unknown"
            method_name = {
                LXMF.LXMessage.OPPORTUNISTIC: "opportunistic",
                LXMF.LXMessage.DIRECT: "link",
                LXMF.LXMessage.PROPAGATED: "propagated",
            }.get(getattr(message, "method", None), "unknown")

            logger.info(
                "Received LXMF from %s [%s, sig=%s]: %.100s",
                source_hash, method_name, sig, content,
            )

            # Extract channel metrics and classify
            metrics = ChannelMetrics.from_lxmessage(message)
            profile = self.profiler.classify(metrics)

            # Dispatch to thread pool (non-blocking)
            if self._message_handler and self._pool:
                # Pass source identity for reply routing
                source_identity = getattr(message, "source", None)
                self._pool.submit(
                    self._process_and_reply, source_hash_raw, content, profile, source_identity,
                )
            else:
                logger.warning("No handler or pool — dropping from %s", source_hash)

        except Exception as e:
            logger.error("Error in LXMF callback: %s", e, exc_info=True)

    def _process_and_reply(
        self, source_hash: str, content: str, profile=None, source_identity=None,
    ):
        """
        Process a message and send the reply. Runs in a thread pool worker.
        """
        try:
            reply = self._message_handler(source_hash, content, profile)
            if reply:
                # Adaptive truncation and splitting
                parts = prepare_reply(reply, profile)
                for i, part in enumerate(parts):
                    if i > 0 and profile:
                        time.sleep(profile.send_delay_ms / 1000)
                    self.send_reply(source_hash, part, source_identity)
        except Exception as e:
            logger.error(
                "Error processing message from %s: %s",
                source_hash[:16], e, exc_info=True,
            )

    def send_reply(self, recipient_hex: str, text: str, source_identity=None) -> bool:
        """
        Send an LXMF text message to a recipient.

        Args:
            recipient_hex: Hex string of the recipient's LXMF hash.
            text: Message content (plain text).
            source_identity: The sender's RNS.Identity (from the incoming message).
                If provided, used directly instead of recalling from store.

        Returns:
            True if the message was dispatched, False on error.
        """
        if not self.router or not self.destination:
            logger.error("Bridge not started — cannot send reply")
            return False

        # Use provided identity or try to recall
        # source_identity may be an RNS.Destination (from message.source)
        # or an RNS.Identity — extract the Identity in either case
        recipient_identity = source_identity
        if recipient_identity is not None:
            # If it's a Destination, extract the underlying Identity
            if hasattr(recipient_identity, "identity"):
                recipient_identity = recipient_identity.identity
        if recipient_identity is None:
            try:
                recipient_hash = bytes.fromhex(recipient_hex)
            except ValueError:
                logger.error("Invalid recipient hash: %s", recipient_hex)
                return False

            # Try recall first
            recipient_identity = RNS.Identity.recall(recipient_hash)

            # If unknown, request path to trigger identity exchange
            if recipient_identity is None:
                logger.info(
                    "Identity unknown for %s — requesting path...",
                    recipient_hex[:16],
                )
                RNS.Transport.request_path(recipient_hash)
                # Poll for identity arrival (up to 8s)
                for _ in range(8):
                    time.sleep(1)
                    recipient_identity = RNS.Identity.recall(recipient_hash)
                    if recipient_identity is not None:
                        break

        if recipient_identity is None:
            logger.error(
                "Unknown recipient identity for %s — cannot send",
                recipient_hex,
            )
            return False

        try:
            # Build the destination for the recipient
            dest = RNS.Destination(
                recipient_identity,
                RNS.Destination.OUT,
                RNS.Destination.SINGLE,
                "lxmf",
                "delivery",
            )

            # Create and dispatch the LXMF message
            lxm = LXMF.LXMessage(
                dest,
                self.destination,
                text,
                desired_method=LXMF.LXMessage.DIRECT,
                include_ticket=True,
            )
            self.router.handle_outbound(lxm)

            logger.info(
                "Reply dispatched to %s (%d bytes)",
                recipient_hex[:16], len(text.encode("utf-8")),
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to send reply to %s: %s",
                recipient_hex[:16], e, exc_info=True,
            )
            return False

    def stop(self):
        """Gracefully shut down the bridge."""
        logger.info("Shutting down Hermes for Reticulum bridge...")
        self._running = False

        if self._pool:
            self._pool.shutdown(wait=False)

        # Reticulum handles cleanup internally

    def run_forever(self):
        """
        Start the bridge and block until interrupted.
        Convenience method for standalone operation.
        """
        self.start()
        self.announce()

        # Set up signal handlers for graceful shutdown
        def _handle_signal(signum, frame):
            logger.info("Signal %s received, shutting down...", signum)
            self._running = False

        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)

        logger.info("Bridge running. Press Ctrl+C to stop.")

        try:
            while self._running:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            self.stop()
