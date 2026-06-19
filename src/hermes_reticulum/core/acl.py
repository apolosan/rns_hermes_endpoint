"""
Access Control — filters incoming messages by sender identity hash.

Supports:
  - Allowlist mode: only listed hashes can interact
  - Open mode: everyone can interact
  - Blocklist mode: listed hashes are rejected
"""

import logging
import os

logger = logging.getLogger("hermes_reticulum.acl")


class AccessControl:
    """
    Controls which LXMF senders can interact with the Hermes agent.

    Configuration via environment variables:
      - HERMES_RETICUM_ALLOW_ALL=true      → open mode (default)
      - HERMES_RETICUM_ALLOWED_USERS=hex1,hex2 → allowlist
      - HERMES_RETICUM_BLOCKED_USERS=hex1,hex2 → blocklist
    """

    def __init__(self):
        self._load_config()

    def _load_config(self):
        """Load ACL config from environment variables."""
        # Allow-all mode
        allow_all = os.getenv("HERMES_RETICUM_ALLOW_ALL", "true").lower()
        self.allow_all = allow_all in ("true", "1", "yes")

        # Allowlist
        allowed_raw = os.getenv("HERMES_RETICUM_ALLOWED_USERS", "")
        self.allowed_users: set[str] = self._parse_hash_set(allowed_raw)

        # Blocklist
        blocked_raw = os.getenv("HERMES_RETICUM_BLOCKED_USERS", "")
        self.blocked_users: set[str] = self._parse_hash_set(blocked_raw)

        logger.info(
            "ACL loaded: allow_all=%s, allowed=%d, blocked=%d",
            self.allow_all,
            len(self.allowed_users),
            len(self.blocked_users),
        )

    @staticmethod
    def _parse_hash_set(raw: str) -> set[str]:
        """Parse comma-separated hex hashes into a normalized set."""
        if not raw.strip():
            return set()
        hashes = set()
        for h in raw.split(","):
            h = h.strip().lower().replace(" ", "").replace(":", "")
            if h and len(h) == 32:  # RNS truncated hash = 16 bytes = 32 hex chars
                hashes.add(h)
            elif h:
                logger.warning("Ignoring invalid hash in ACL: %s (expected 32 hex chars)", h)
        return hashes

    def is_allowed(self, sender_hash: str) -> bool:
        """
        Check if a sender is allowed to interact with the agent.

        Args:
            sender_hash: Hex string of the sender's LXMF hash (with or without colons).

        Returns:
            True if the sender is permitted.
        """
        # Normalize
        normalized = sender_hash.lower().replace(":", "").replace(" ", "")

        # Blocklist takes priority
        if normalized in self.blocked_users:
            logger.info("Blocked sender: %s", sender_hash)
            return False

        # Allow-all mode
        if self.allow_all:
            return True

        # Allowlist mode
        if normalized in self.allowed_users:
            return True

        logger.info("Sender not in allowlist: %s", sender_hash)
        return False

    @property
    def mode(self) -> str:
        """Human-readable ACL mode."""
        if self.allow_all:
            return "open"
        return "allowlist" if self.allowed_users else "closed"

    def __repr__(self) -> str:
        return (
            f"AccessControl(mode={self.mode}, "
            f"allowed={len(self.allowed_users)}, "
            f"blocked={len(self.blocked_users)})"
        )
