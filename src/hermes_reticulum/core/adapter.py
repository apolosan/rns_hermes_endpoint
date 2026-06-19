"""
Message Adapter — truncates and splits responses to fit channel constraints.

Works with ChannelProfile to ensure outgoing LXMF messages never exceed
the bandwidth limits of the detected transport.
"""

import logging

logger = logging.getLogger("hermes_reticulum.adapter")


def truncate_to_limit(text: str, max_chars: int) -> str:
    """
    Truncate text to max_chars, respecting sentence/word boundaries.

    Strategy:
    1. If text fits, return as-is
    2. Try to cut at the last sentence boundary (.) within limit
    3. Fall back to last word boundary (space)
    4. Hard truncate with ellipsis
    """
    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars]

    # Try sentence boundary (keep at least 50% of content)
    last_period = truncated.rfind(".")
    if last_period > max_chars * 0.5:
        return truncated[: last_period + 1]

    # Try word boundary
    last_space = truncated.rfind(" ")
    if last_space > max_chars * 0.5:
        return truncated[:last_space] + "..."

    # Hard truncate
    return truncated + "..."


def split_message(text: str, max_chars: int) -> list[str]:
    """
    Split a long message into multiple parts that fit within max_chars.

    Each part is numbered [N/Total] when there are multiple parts.
    Splitting respects sentence boundaries when possible.
    """
    if len(text) <= max_chars:
        return [text]

    parts = []
    remaining = text

    while remaining:
        if len(remaining) <= max_chars:
            parts.append(remaining)
            break

        # Find a good split point
        cut = _find_split_point(remaining, max_chars)
        parts.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()

    # Number parts if multiple
    if len(parts) > 1:
        total = len(parts)
        parts = [f"[{i + 1}/{total}] {p}" for i, p in enumerate(parts)]

    return parts


def _find_split_point(text: str, max_chars: int) -> int:
    """
    Find the best position to split text, preferring sentence > paragraph > word boundaries.
    """
    candidates = text[:max_chars]

    # Prefer splitting after a sentence (. ! ?)
    for punct in [". ", "! ", "? ", ".\n", "!\n", "?\n"]:
        idx = candidates.rfind(punct)
        if idx > max_chars * 0.4:
            return idx + len(punct)

    # Prefer splitting at paragraph boundary
    idx = candidates.rfind("\n\n")
    if idx > max_chars * 0.3:
        return idx + 2

    # Split at line break
    idx = candidates.rfind("\n")
    if idx > max_chars * 0.3:
        return idx + 1

    # Split at word boundary
    idx = candidates.rfind(" ")
    if idx > max_chars * 0.3:
        return idx + 1

    # Hard split
    return max_chars


def prepare_reply(text: str, profile) -> list[str]:
    """
    Full pipeline: truncate → split → return list of sendable parts.

    Args:
        text: Raw reply from Hermes.
        profile: ChannelProfile with limits.

    Returns:
        List of message strings ready to send via LXMF.
    """
    if not text:
        return []

    # Truncate to profile limit
    truncated = truncate_to_limit(text, profile.max_response_chars)

    # Split if needed
    parts = split_message(truncated, profile.max_response_chars)

    logger.debug(
        "Reply prepared: %d chars → %d parts (max=%d)",
        len(text), len(parts), profile.max_response_chars,
    )

    return parts
