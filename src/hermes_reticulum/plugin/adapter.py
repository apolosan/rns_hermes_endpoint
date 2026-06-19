"""
Reticulum Platform Adapter for the Hermes Gateway.

Bridges LXMF messages into the Hermes gateway event loop so that
the agent can process them like any other messaging platform.
"""

import asyncio
import logging
import os

logger = logging.getLogger("hermes_reticulum.adapter")


def check_reticulum_requirements() -> bool:
    """Check if RNS and LXMF Python packages are available."""
    try:
        import LXMF  # noqa: F401
        import RNS  # noqa: F401
        return True
    except ImportError:
        return False


class ReticulumPlatformAdapter:
    """
    Platform adapter that bridges Reticulum/LXMF to the Hermes gateway.

    This adapter:
    1. Starts the LXM Router and listens for incoming messages
    2. Converts LXMF messages into gateway MessageEvents
    3. Sends replies back via LXMF

    Designed to work with the Hermes plugin system (platform_registry).
    """

    def __init__(self, config):
        """
        Initialize the adapter.

        Args:
            config: PlatformConfig from the gateway, with .extra dict
                    containing Reticulum-specific settings.
        """
        self.config = config
        extra = getattr(config, "extra", {}) or {}

        default_name = "Hermes for Reticulum"
        self.display_name = extra.get(
            "display_name",
            os.getenv("RETICULUM_DISPLAY_NAME", default_name),
        )
        self.storage_path = extra.get("storage_path", os.getenv("RETICULUM_STORAGE", None))
        self.stamp_cost = int(extra.get("stamp_cost", os.getenv("RETICULUM_STAMP_COST", "8")))
        self.hermes_bin = extra.get("hermes_bin", os.getenv("HERMES_BIN", "hermes"))
        self.timeout = int(extra.get("timeout", os.getenv("HERMES_TIMEOUT", "300")))

        # Internal state
        self._bridge = None
        self._hermes_client = None
        self._acl = None
        self._handle_message = None  # gateway callback
        self._loop: asyncio.AbstractEventLoop | None = None
        self._connected = False

    def connect(self) -> bool:
        """
        Start the LXMF bridge and begin listening for messages.
        Called by the gateway during startup.
        """
        try:
            from hermes_reticulum.core.acl import AccessControl
            from hermes_reticulum.core.bridge import LXMFBridge
            from hermes_reticulum.core.hermes_client import HermesClient

            self._acl = AccessControl()
            self._hermes_client = HermesClient(
                hermes_bin=self.hermes_bin,
                timeout=self.timeout,
            )

            self._bridge = LXMFBridge(
                display_name=self.display_name,
                storage_path=self.storage_path,
                stamp_cost=self.stamp_cost,
            )

            # Wire the LXMF callback to our gateway handler
            self._bridge.set_message_handler(self._on_lxmf_message)
            self._bridge.start()
            self._bridge.announce()

            self._connected = True
            logger.info(
                "Reticulum adapter connected — address: %s",
                self._bridge.address,
            )
            return True

        except Exception as e:
            logger.error("Failed to connect Reticulum adapter: %s", e, exc_info=True)
            return False

    def disconnect(self):
        """Stop the LXMF bridge."""
        if self._bridge:
            self._bridge.stop()
        self._connected = False
        logger.info("Reticulum adapter disconnected")

    def _on_lxmf_message(self, source_hash: str, content: str) -> str | None:
        """
        Callback from the LXMF bridge. Called synchronously for each
        incoming message. Processes it and returns a reply.
        """
        # ACL check
        if self._acl and not self._acl.is_allowed(source_hash):
            return "Access not authorized."

        # Call Hermes
        if self._hermes_client:
            return self._hermes_client.chat(content)

        return None

    @property
    def address(self) -> str | None:
        """The LXMF address of this adapter."""
        if self._bridge:
            return self._bridge.address
        return None

    @property
    def is_connected(self) -> bool:
        return self._connected

    def send_message(self, chat_id: str, text: str) -> bool:
        """
        Send a text message to a chat_id (LXMF hex hash).
        Used by the gateway's send_message tool.
        """
        if self._bridge:
            return self._bridge.send_reply(chat_id, text)
        return False
