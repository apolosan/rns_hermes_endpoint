"""
Hermes Gateway Plugin — registers Reticulum/LXMF as a native platform.

Drop this plugin into ~/.hermes/plugins/reticulum/ and restart the gateway
to enable Reticulum as a first-class messaging platform alongside Telegram,
Discord, WhatsApp, etc.
"""

from hermes_reticulum.plugin.adapter import ReticulumAdapter, check_reticulum_requirements
from hermes_reticulum.plugin.registration import register

__all__ = ["ReticulumAdapter", "check_reticulum_requirements", "register"]
