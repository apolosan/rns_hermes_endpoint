"""
Tests for the adaptive response system (profiler + adapter).
"""

from hermes_reticulum.core.adapter import (
    prepare_reply,
    split_message,
    truncate_to_limit,
)
from hermes_reticulum.core.profiler import (
    PROFILES,
    ChannelMetrics,
    ChannelProfiler,
)

# ═══════════════════════════════════════════════════════════════
# ChannelProfiler tests
# ═══════════════════════════════════════════════════════════════


class TestChannelProfiler:
    """Test channel classification logic."""

    def test_tcp_high_bitrate(self):
        """High bitrate → tcp_default."""
        profiler = ChannelProfiler()
        m = ChannelMetrics(bitrate=1_000_000, method=2)
        p = profiler.classify(m)
        assert p.name == "tcp_default"

    def test_lora_low_bitrate_good_signal(self):
        """Low bitrate + good signal → lora_standard."""
        profiler = ChannelProfiler()
        m = ChannelMetrics(bitrate=300, rssi=-90, snr=10, method=2)
        p = profiler.classify(m)
        assert p.name == "lora_standard"

    def test_lora_low_bitrate_weak_signal(self):
        """Low bitrate + weak signal → lora_constrained."""
        profiler = ChannelProfiler()
        m = ChannelMetrics(bitrate=300, rssi=-115, snr=3, method=2)
        p = profiler.classify(m)
        assert p.name == "lora_constrained"

    def test_opportunistic_no_bitrate(self):
        """OPPORTUNISTIC method without bitrate → infer LoRa → lora_standard."""
        profiler = ChannelProfiler()
        m = ChannelMetrics(method=1)  # OPPORTUNISTIC
        p = profiler.classify(m)
        assert p.name == "lora_standard"

    def test_direct_no_bitrate(self):
        """DIRECT method without link → infer LoRa → lora_standard."""
        profiler = ChannelProfiler()
        m = ChannelMetrics(method=2, is_link=False)
        p = profiler.classify(m)
        assert p.name == "lora_standard"

    def test_direct_with_link_no_bitrate(self):
        """DIRECT + link (TCP) → tcp_default."""
        profiler = ChannelProfiler()
        m = ChannelMetrics(method=2, is_link=True)
        p = profiler.classify(m)
        assert p.name == "tcp_default"

    def test_small_mtu_infers_lora(self):
        """Small HW_MTU (< 300) → infer LoRa."""
        profiler = ChannelProfiler()
        m = ChannelMetrics(hw_mtu=256, method=2)
        p = profiler.classify(m)
        assert p.name == "lora_standard"

    def test_many_hops_constrained(self):
        """Hops > 3 → constrained."""
        profiler = ChannelProfiler()
        m = ChannelMetrics(bitrate=300, hops=5, rssi=-90, snr=10)
        p = profiler.classify(m)
        assert p.name == "lora_constrained"

    def test_cache_hit(self):
        """Same source hash returns cached profile."""
        profiler = ChannelProfiler()
        m1 = ChannelMetrics(bitrate=300, rssi=-90, snr=10, source_hash="aa" * 16)
        m2 = ChannelMetrics(bitrate=1_000_000, source_hash="aa" * 16)

        p1 = profiler.classify(m1)
        p2 = profiler.classify(m2)  # Should return cached lora_standard

        assert p1.name == "lora_standard"
        assert p2.name == "lora_standard"  # Cached, not reclassified

    def test_cache_invalidation(self):
        """Cache can be cleared."""
        profiler = ChannelProfiler()
        m1 = ChannelMetrics(bitrate=300, source_hash="bb" * 16)
        m2 = ChannelMetrics(bitrate=1_000_000, source_hash="bb" * 16)

        p1 = profiler.classify(m1)
        assert p1.name == "lora_standard"

        profiler.invalidate_cache("bb" * 16)
        p2 = profiler.classify(m2)
        assert p2.name == "tcp_default"

    def test_no_metrics_fallback(self):
        """No metrics at all → default profile."""
        profiler = ChannelProfiler()
        m = ChannelMetrics()  # All None/defaults
        p = profiler.classify(m)
        # Without bitrate or method, infers from defaults
        assert p.name in ("tcp_default", "lora_standard")


# ═══════════════════════════════════════════════════════════════
# ChannelProfile tests
# ═══════════════════════════════════════════════════════════════


class TestChannelProfile:
    """Test profile properties."""

    def test_all_profiles_have_required_fields(self):
        """Every profile has all required fields."""
        for name, p in PROFILES.items():
            assert p.name == name
            assert p.max_response_chars > 0
            assert p.max_tokens_hint > 0
            assert p.verbosity in ("minimal", "concise", "normal")
            assert p.instruction  # Non-empty

    def test_lora_profiles_are_smaller_than_tcp(self):
        """LoRa profiles have smaller limits than TCP."""
        lora_c = PROFILES["lora_constrained"]
        lora_s = PROFILES["lora_standard"]
        tcp = PROFILES["tcp_default"]

        assert lora_c.max_response_chars < lora_s.max_response_chars
        assert lora_s.max_response_chars < tcp.max_response_chars

    def test_max_response_bytes(self):
        """max_response_bytes is 3x chars (UTF-8 worst case)."""
        p = PROFILES["tcp_default"]
        assert p.max_response_bytes == p.max_response_chars * 3


# ═══════════════════════════════════════════════════════════════
# truncate_to_limit tests
# ═══════════════════════════════════════════════════════════════


class TestTruncate:
    """Test intelligent truncation."""

    def test_short_text_unchanged(self):
        assert truncate_to_limit("Hello", 100) == "Hello"

    def test_exact_limit_unchanged(self):
        assert truncate_to_limit("Hello", 5) == "Hello"

    def test_truncate_at_sentence(self):
        result = truncate_to_limit("Hello world. How are you today?", 15)
        assert result == "Hello world."

    def test_truncate_at_word(self):
        result = truncate_to_limit("Hello beautiful world today", 12)
        # "Hello beautiful" = 15 chars, "Hello " = 6 chars (50% of 12)
        # Should cut at word boundary after position 6
        assert "..." in result
        assert result.startswith("Hello")

    def test_hard_truncate(self):
        result = truncate_to_limit("ABCDEFGHIJ", 5)
        assert len(result) <= 8  # 5 + "..."
        assert result.startswith("ABCDE")


# ═══════════════════════════════════════════════════════════════
# split_message tests
# ═══════════════════════════════════════════════════════════════


class TestSplit:
    """Test message splitting."""

    def test_short_message_no_split(self):
        result = split_message("Hello", 100)
        assert result == ["Hello"]

    def test_long_message_split(self):
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        result = split_message(text, 30)
        assert len(result) > 1
        # All parts should be within limit (with numbering prefix)
        for part in result:
            assert len(part) <= 40  # Some slack for [N/M] prefix

    def test_numbered_parts(self):
        text = "A. " * 50  # ~150 chars
        result = split_message(text, 50)
        assert len(result) > 1
        assert result[0].startswith("[1/")
        assert result[-1].startswith(f"[{len(result)}/")


# ═══════════════════════════════════════════════════════════════
# prepare_reply tests
# ═══════════════════════════════════════════════════════════════


class TestPrepareReply:
    """Test the full reply preparation pipeline."""

    def test_short_reply(self):
        profile = PROFILES["tcp_default"]
        result = prepare_reply("Hello!", profile)
        assert result == ["Hello!"]

    def test_long_reply_lora(self):
        profile = PROFILES["lora_constrained"]
        # Text that's longer than max_response_chars before truncation
        long_text = "A" * 500
        result = prepare_reply(long_text, profile)
        # Truncation reduces to 200 chars, then split may or may not be needed
        assert len(result) >= 1
        # Total chars should be <= max_response_chars (with numbering)
        total = sum(len(p) for p in result)
        assert total <= profile.max_response_chars + 20  # Some slack for [N/M]

    def test_empty_reply(self):
        profile = PROFILES["default"]
        assert prepare_reply("", profile) == []
        assert prepare_reply(None, profile) == []
