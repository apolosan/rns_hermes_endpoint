"""
Channel Profiler — detects transport type and selects optimal response profile.

Uses RNS/LXMF telemetry (RSSI, SNR, bitrate, delivery method) to classify
the channel between client and endpoint, then selects a response profile
that optimizes for bandwidth, latency, and token efficiency.
"""

import logging
import time
from dataclasses import dataclass

import LXMF
import RNS

logger = logging.getLogger("hermes_reticulum.profiler")

# ═══════════════════════════════════════════════════════════════
# Bitrate thresholds (bits per second)
# ═══════════════════════════════════════════════════════════════
LORA_MAX_BITRATE = 50_000       # LoRa SF12: ~250bps, SF7: ~5.5kbps
                                  # Threshold: 50kbps separates LoRa from TCP
TCP_MIN_BITRATE = 100_000       # Conservative minimum for TCP/Ethernet

# ═══════════════════════════════════════════════════════════════
# RSSI thresholds (dBm)
# ═══════════════════════════════════════════════════════════════
RSSI_POOR = -110                # Below this = very weak signal
RSSI_FAIR = -95                 # Above this = acceptable signal

# ═══════════════════════════════════════════════════════════════
# SNR thresholds (dB)
# ═══════════════════════════════════════════════════════════════
SNR_POOR = 5                    # Below this = noisy channel
SNR_GOOD = 10                   # Above this = clean channel


@dataclass
class ChannelMetrics:
    """
    Transport metrics extracted from a received LXMF message and RNS state.
    """
    rssi: float | None = None           # Signal strength (dBm)
    snr: float | None = None            # Signal-to-noise ratio (dB)
    method: int = 0                     # Delivery method (DIRECT/OPPORTUNISTIC/PROPAGATED)
    bitrate: int | None = None          # Next-hop interface bitrate (bps)
    hw_mtu: int | None = None           # Hardware MTU of next-hop interface (bytes)
    hops: int | None = None             # Number of hops to destination
    source_hash: str = ""               # Hex string of source identity
    transport_encrypted: bool = False   # Whether transport encryption was used
    is_link: bool = False               # Whether delivery was via established link

    @classmethod
    def from_lxmessage(cls, message) -> "ChannelMetrics":
        """
        Extract metrics from a received LXMessage and RNS Transport state.

        Args:
            message: An LXMF.LXMessage instance from the delivery callback.
        """
        # Source hash
        src_bytes = message.source_hash
        source_hash = src_bytes.hex() if isinstance(src_bytes, bytes) else str(src_bytes)

        # RSSI and SNR from the message (if available from link/radio)
        rssi = getattr(message, "rssi", None)
        snr = getattr(message, "snr", None)

        # Delivery method
        method = getattr(message, "method", 0)

        # Transport-level metrics (require RNS to know the route)
        bitrate = None
        hw_mtu = None
        hops = None
        try:
            bitrate = RNS.Transport.next_hop_interface_bitrate(src_bytes)
        except Exception:
            pass
        try:
            hw_mtu = RNS.Transport.next_hop_interface_hw_mtu(src_bytes)
        except Exception:
            pass
        try:
            hops = RNS.Transport.hops_to(src_bytes)
        except Exception:
            pass

        return cls(
            rssi=rssi,
            snr=snr,
            method=method,
            bitrate=bitrate,
            hw_mtu=hw_mtu,
            hops=hops,
            source_hash=source_hash,
            transport_encrypted=getattr(message, "transport_encrypted", False),
            is_link=(getattr(message, "method", None) == LXMF.LXMessage.DIRECT),
        )


@dataclass
class ChannelProfile:
    """
    Response profile selected for a specific channel type.

    Controls how the agent formats and limits its response to match
    the bandwidth constraints of the transport.
    """
    name: str                               # Profile identifier
    max_response_chars: int                 # Max characters per reply
    max_tokens_hint: int                    # Hint for Hermes (via prompt)
    verbosity: str                          # "minimal", "concise", "normal"
    format: str                             # "plain", "plain_text"
    split_long: bool                        # Whether to split oversized replies
    send_delay_ms: int                      # Delay between split parts (ms)
    instruction: str                        # System instruction injected into prompt

    @property
    def max_response_bytes(self) -> int:
        """Max response size in bytes (UTF-8)."""
        return self.max_response_chars * 3  # Worst case: 3 bytes per char


# ═══════════════════════════════════════════════════════════════
# Default profiles
# ═══════════════════════════════════════════════════════════════

PROFILES = {
    # LoRa with weak signal — maximize reliability
    "lora_constrained": ChannelProfile(
        name="lora_constrained",
        max_response_chars=200,
        max_tokens_hint=100,
        verbosity="minimal",
        format="plain",
        split_long=True,
        send_delay_ms=2000,
        instruction=(
            "Reply in at most 3 short, direct sentences. "
            "No formatting, no examples, no long explanations. "
            "Maximum 200 characters. Get straight to the point."
        ),
    ),

    # LoRa with good signal — slightly more room
    "lora_standard": ChannelProfile(
        name="lora_standard",
        max_response_chars=500,
        max_tokens_hint=200,
        verbosity="concise",
        format="plain",
        split_long=True,
        send_delay_ms=1500,
        instruction=(
            "Reply concisely in up to 5 sentences. "
            "No markdown formatting. Be direct. "
            "Maximum 500 characters."
        ),
    ),

    # TCP — good bandwidth, but still no markdown (LXMF limitation)
    "tcp_default": ChannelProfile(
        name="tcp_default",
        max_response_chars=4000,
        max_tokens_hint=2000,
        verbosity="normal",
        format="plain_text",
        split_long=True,
        send_delay_ms=500,
        instruction=(
            "Reply clearly and completely. "
            "Use plain text without markdown. "
            "Maximum 4000 characters."
        ),
    ),

    # Fallback — unknown channel
    "default": ChannelProfile(
        name="default",
        max_response_chars=1000,
        max_tokens_hint=500,
        verbosity="normal",
        format="plain",
        split_long=True,
        send_delay_ms=1000,
        instruction=(
            "Reply clearly and concisely. "
            "Maximum 1000 characters."
        ),
    ),
}


class ChannelProfiler:
    """
    Classifies channels and selects response profiles based on transport metrics.

    Features:
    - Automatic LoRa vs TCP detection via bitrate
    - Signal quality assessment via RSSI/SNR
    - Per-source caching with TTL (avoids repeated Transport lookups)
    - Graceful fallback when metrics are unavailable
    """

    def __init__(
        self,
        profiles: dict[str, ChannelProfile] | None = None,
        cache_ttl: int = 300,
    ):
        """
        Args:
            profiles: Custom profile dict (name → ChannelProfile).
            cache_ttl: Cache lifetime in seconds.
        """
        self.profiles = profiles or PROFILES
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[ChannelProfile, float]] = {}

    def classify(self, metrics: ChannelMetrics) -> ChannelProfile:
        """
        Select the optimal response profile for a given set of metrics.

        Classification logic:
        1. Check bitrate: < 50kbps → LoRa, else → TCP
        2. If LoRa: check RSSI/SNR for constrained vs standard
        3. Cache result per source hash
        """
        # Cache check
        cached = self._get_cached(metrics.source_hash)
        if cached is not None:
            logger.debug("Profile cache hit for %s: %s", metrics.source_hash[:16], cached.name)
            return cached

        # Classify
        profile = self._classify(metrics)

        # Cache
        self._cache[metrics.source_hash] = (profile, time.time())

        logger.info(
            "Channel classified for %s: %s (bitrate=%s, rssi=%s, snr=%s, method=%d)",
            metrics.source_hash[:16],
            profile.name,
            metrics.bitrate,
            metrics.rssi,
            metrics.snr,
            metrics.method,
        )

        return profile

    def _classify(self, m: ChannelMetrics) -> ChannelProfile:
        """Internal classification logic."""

        # ── Step 1: Determine if LoRa ──
        is_lora = False

        if m.bitrate is not None:
            is_lora = m.bitrate < LORA_MAX_BITRATE
        else:
            # Infer from delivery method
            if m.method == LXMF.LXMessage.OPPORTUNISTIC:
                is_lora = True  # Single-packet = likely LoRa
            elif m.method == LXMF.LXMessage.DIRECT and not m.is_link:
                is_lora = True  # No established link = likely LoRa
            elif m.hw_mtu is not None and m.hw_mtu < 300:
                is_lora = True  # Small MTU = likely LoRa

        if not is_lora:
            return self.profiles["tcp_default"]

        # ── Step 2: LoRa quality assessment ──
        is_constrained = False

        if m.rssi is not None and m.rssi < RSSI_POOR:
            is_constrained = True
            logger.debug("LoRa constrained: RSSI=%s < %s", m.rssi, RSSI_POOR)

        if m.snr is not None and m.snr < SNR_POOR:
            is_constrained = True
            logger.debug("LoRa constrained: SNR=%s < %s", m.snr, SNR_POOR)

        if m.hops is not None and m.hops > 3:
            is_constrained = True
            logger.debug("LoRa constrained: hops=%s > 3", m.hops)

        if is_constrained:
            return self.profiles["lora_constrained"]

        return self.profiles["lora_standard"]

    def _get_cached(self, source_hash: str) -> ChannelProfile | None:
        """Return cached profile if still valid."""
        if source_hash in self._cache:
            profile, ts = self._cache[source_hash]
            if time.time() - ts < self.cache_ttl:
                return profile
            del self._cache[source_hash]
        return None

    def invalidate_cache(self, source_hash: str | None = None):
        """Clear cache for a specific source or all sources."""
        if source_hash:
            self._cache.pop(source_hash, None)
        else:
            self._cache.clear()
