"""
Tests for Hermes for Reticulum.
"""

from unittest.mock import MagicMock

from hermes_reticulum.core.acl import AccessControl
from hermes_reticulum.core.hermes_client import HermesClient, find_hermes_bin


class TestACL:
    """Test the access control module."""

    def test_open_mode(self, monkeypatch):
        monkeypatch.setenv("HERMES_RETICUM_ALLOW_ALL", "true")
        monkeypatch.delenv("HERMES_RETICUM_ALLOWED_USERS", raising=False)
        monkeypatch.delenv("HERMES_RETICUM_BLOCKED_USERS", raising=False)

        acl = AccessControl()
        assert acl.mode == "open"
        assert acl.is_allowed("aabbccdd" * 4) is True

    def test_allowlist_mode(self, monkeypatch):
        monkeypatch.setenv("HERMES_RETICUM_ALLOW_ALL", "false")
        monkeypatch.setenv("HERMES_RETICUM_ALLOWED_USERS", "aabbccdd" * 4)
        monkeypatch.delenv("HERMES_RETICUM_BLOCKED_USERS", raising=False)

        acl = AccessControl()
        assert acl.mode == "allowlist"
        assert acl.is_allowed("aabbccdd" * 4) is True
        assert acl.is_allowed("11223344" * 4) is False

    def test_blocklist(self, monkeypatch):
        monkeypatch.setenv("HERMES_RETICUM_ALLOW_ALL", "true")
        monkeypatch.setenv("HERMES_RETICUM_BLOCKED_USERS", "deadbeef" * 4)
        monkeypatch.delenv("HERMES_RETICUM_ALLOWED_USERS", raising=False)

        acl = AccessControl()
        assert acl.is_allowed("deadbeef" * 4) is False
        assert acl.is_allowed("aabbccdd" * 4) is True

    def test_invalid_hash_ignored(self, monkeypatch):
        monkeypatch.setenv("HERMES_RETICUM_ALLOW_ALL", "false")
        # short=bad, toolong=bad, valid=good
        valid = "1122334411223344aabbccdd11223344"
        monkeypatch.setenv("HERMES_RETICUM_ALLOWED_USERS", f"short,toolonghashvalue,{valid}")
        monkeypatch.delenv("HERMES_RETICUM_BLOCKED_USERS", raising=False)

        acl = AccessControl()
        # Only the valid 32-char hash should be in the set
        assert len(acl.allowed_users) == 1


class TestFindHermesBin:
    """Test hermes binary detection."""

    def test_find_in_path(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/hermes" if x == "hermes" else None)
        assert find_hermes_bin() == "/usr/bin/hermes"

    def test_find_known_location(self, monkeypatch, tmp_path):
        monkeypatch.setattr("shutil.which", lambda x: None)
        # Create a fake hermes binary
        fake = tmp_path / "hermes"
        fake.write_text("#!/bin/sh\necho ok")
        fake.chmod(0o755)

        # Patch the candidates list
        import hermes_reticulum.core.hermes_client as hc
        original = hc._HERMES_CANDIDATES
        hc._HERMES_CANDIDATES = [str(fake)]
        try:
            assert find_hermes_bin() == str(fake)
        finally:
            hc._HERMES_CANDIDATES = original

    def test_not_found(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda x: None)
        import hermes_reticulum.core.hermes_client as hc
        original = hc._HERMES_CANDIDATES
        hc._HERMES_CANDIDATES = []
        try:
            assert find_hermes_bin() is None
        finally:
            hc._HERMES_CANDIDATES = original


class TestHermesClient:
    """Test the Hermes client (mocked)."""

    def test_chat_returns_reply(self, monkeypatch):
        def mock_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = "Hello! How can I help you?"
            result.stderr = ""
            return result

        monkeypatch.setattr("subprocess.run", mock_run)
        monkeypatch.setattr(
            "hermes_reticulum.core.hermes_client.find_hermes_bin",
            lambda: "/usr/bin/hermes",
        )

        client = HermesClient()
        reply = client.chat("Hello")
        assert reply == "Hello! How can I help you?"

    def test_chat_handles_timeout(self, monkeypatch):
        import subprocess as sp

        def mock_run(cmd, **kwargs):
            raise sp.TimeoutExpired(cmd=cmd, timeout=300)

        monkeypatch.setattr("subprocess.run", mock_run)
        monkeypatch.setattr(
            "hermes_reticulum.core.hermes_client.find_hermes_bin",
            lambda: "/usr/bin/hermes",
        )

        client = HermesClient(timeout=300)
        reply = client.chat("Hello")
        assert "timeout" in reply.lower() or "exceeded" in reply.lower()

    def test_chat_handles_file_not_found(self, monkeypatch):
        def mock_run(cmd, **kwargs):
            raise FileNotFoundError("hermes not found")

        monkeypatch.setattr("subprocess.run", mock_run)
        monkeypatch.setattr(
            "hermes_reticulum.core.hermes_client.find_hermes_bin",
            lambda: "/nonexistent/hermes",
        )

        client = HermesClient()
        reply = client.chat("Hello")
        assert "not found" in reply.lower()

    def test_chat_handles_nonzero_exit(self, monkeypatch):
        def mock_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 1
            result.stdout = ""
            result.stderr = "Error: something broke"
            return result

        monkeypatch.setattr("subprocess.run", mock_run)
        monkeypatch.setattr(
            "hermes_reticulum.core.hermes_client.find_hermes_bin",
            lambda: "/usr/bin/hermes",
        )

        client = HermesClient()
        reply = client.chat("Hello")
        assert "error" in reply.lower()


class TestVersion:
    """Test package metadata."""

    def test_version_importable(self):
        from hermes_reticulum import __version__
        assert __version__ == "0.1.0"
