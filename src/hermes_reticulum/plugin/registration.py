"""
Plugin Registration — registers Reticulum/LXMF with the Hermes gateway.

This module is the entry point called by the Hermes plugin system.
It registers a PlatformEntry so the gateway discovers and instantiates
the Reticulum adapter automatically.
"""

import logging
import os

logger = logging.getLogger("hermes_reticulum.registration")


def register(ctx):
    """
    Called by the Hermes plugin system to register the Reticulum platform.

    Args:
        ctx: PluginContext with register_platform() method.
    """
    from hermes_reticulum.plugin.adapter import (
        ReticulumPlatformAdapter,
        check_reticulum_requirements,
    )

    def validate_config(config) -> bool:
        """Validate that the platform config is usable."""
        return True  # Minimal config needed — everything has defaults

    def is_connected(config) -> bool:
        """Check if the adapter is currently connected."""
        # This is called by the gateway status system
        return os.getenv("RETICULUM_CONNECTED", "false").lower() == "true"

    def env_enablement() -> dict | None:
        """Seed PlatformConfig.extra from environment variables."""
        extra = {}
        display_name = os.getenv("RETICULUM_DISPLAY_NAME")
        if display_name:
            extra["display_name"] = display_name

        storage = os.getenv("RETICULUM_STORAGE")
        if storage:
            extra["storage_path"] = storage

        stamp = os.getenv("RETICULUM_STAMP_COST")
        if stamp:
            extra["stamp_cost"] = int(stamp)

        return extra if extra else None

    # Build the platform entry
    try:
        from gateway.platform_registry import PlatformEntry
    except ImportError:
        # If running standalone (not inside gateway), skip registration
        logger.debug("Not running inside Hermes gateway — skipping platform registration")
        return

    ctx.register_platform(PlatformEntry(
        name="reticulum",
        label="Reticulum (LXMF)",
        adapter_factory=lambda cfg: ReticulumPlatformAdapter(cfg),
        check_fn=check_reticulum_requirements,
        validate_config=validate_config,
        is_connected=is_connected,
        env_enablement_fn=env_enablement,
        required_env=[],
        optional_env=["RETICULUM_DISPLAY_NAME", "RETICULUM_STORAGE", "RETICULUM_STAMP_COST"],
        install_hint="pip install hermes-reticulum",
        emoji="🛜",
        source="plugin",
        max_message_length=1024,
        pii_safe=True,
        platform_hint=(
            "You are on Reticulum/LXMF (via Sideband). "
            "Messages are plain text only — no markdown formatting. "
            "Keep responses concise due to bandwidth constraints (especially over LoRa). "
            "The connection may be off-grid, so be efficient and clear."
        ),
        cron_deliver_env_var="RETICULUM_HOME_CHANNEL",
        allowed_users_env="HERMES_RETICUM_ALLOWED_USERS",
        allow_all_env="HERMES_RETICUM_ALLOW_ALL",
    ))

    logger.info("Reticulum/LXMF platform registered")
