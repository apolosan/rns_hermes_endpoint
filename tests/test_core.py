"""
Basic tests for Hermes for Reticulum.
"""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestACL:
    """Test the access control module."""

    def test_open_mode(self, monkeypatch):
        monkeypatch.setenv("HERMES_RETICUM_ALLOW_ALL", "true")
        monkeypatch.delenv("HERMES_RETICUM_ALLOWED_USERS", raising=False)
        monkeypatch.delenv("HERMES_RETICUM_BLOCKED_USERS", raising=False)

        from hermes_reticulum.core.acl import AccessControl
        acl = AccessControl()

        assert acl.mode == "open"
        assert acl.is_allowed("aabbccdd" * 4) is True

    def test_allowlist_mode(self, monkeypatch):
        monkeypatch.setenv("HERMES_RETICUM_ALLOW_ALL", "false")
        monkeypatch.setenv("HERMES_RETICUM_ALLOWED_USERS", "aabbccdd" * 4)
        monkeypatch.delenv("HERMES_RETICUM_BLOCKED_USERS", raising=False)

        from hermes_reticulum.core.acl import AccessControl
        acl = AccessControl()

        assert acl.mode == "allowlist"
        assert acl.is_allowed("aabbccdd" * 4) is True
        assert acl.is_allowed("11223344" * 4) is False

    def test_blocklist(self, monkeypatch):
        monkeypatch.setenv("HERMES_RETICUM_ALLOW_ALL", "true")
        monkeypatch.setenv("HERMES_RETICUM_BLOCKED_USERS", "deadbeef" * 4)
        monkeypatch.delenv("HERMES_RETICUM_ALLOWED_USERS", raising=False)

        from hermes_reticulum.core.acl import AccessControl
        acl = AccessControl()

        assert acl.is_allowed("deadbeef" * 4) is False
        assert acl.is_allowed("aabbccdd" * 4) is True


class TestHermesClient:
    """Test the Hermes client (mocked)."""

    def test_chat_returns_reply(self, monkeypatch):
        from hermes_reticulum.core.hermes_client import HermesClient

        def mock_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = "Hello! How can I help you?"
            result.stderr = ""
            return result

        monkeypatch.setattr("subprocess.run", mock_run)

        client = HermesClient()
        reply = client.chat("Hello")
        assert reply == "Hello! How can I help you?"

    def test_chat_handles_timeout(self, monkeypatch):
        import subprocess as sp
        from hermes_reticulum.core.hermes_client import HermesClient

        def mock_run(cmd, **kwargs):
            raise sp.TimeoutExpired(cmd=cmd, timeout=300)

        monkeypatch.setattr("subprocess.run", mock_run)

        client = HermesClient(timeout=300)
        reply = client.chat("Hello")
        assert "timeout" in reply.lower() or "excedeu" in reply.lower()


class TestVersion:
    """Test package metadata."""

    def test_version_importable(self):
        from hermes_reticulum import __version__
        assert __version__ == "0.1.0"
