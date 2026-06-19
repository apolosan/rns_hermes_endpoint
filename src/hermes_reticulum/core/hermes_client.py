"""
Hermes Integration — calls Hermes Agent to process messages and return replies.

Supports two modes:
  1. CLI mode (default): calls `hermes chat -q` as a subprocess
  2. Future: direct Python import when Hermes is importable
"""

import logging
import os
import subprocess

logger = logging.getLogger("hermes_reticulum.hermes")


class HermesClient:
    """
    Client that sends messages to Hermes Agent and returns replies.

    Handles the subprocess call, timeout, output parsing, and error recovery.
    """

    def __init__(
        self,
        hermes_bin: str = "hermes",
        timeout: int = 300,
        source_tag: str = "reticulum",
        extra_args: list[str] | None = None,
    ):
        """
        Args:
            hermes_bin: Path to the hermes CLI binary.
            timeout: Max seconds to wait for a reply.
            source_tag: Source tag passed to --source for session tracking.
            extra_args: Additional args to pass to hermes chat.
        """
        self.hermes_bin = hermes_bin
        self.timeout = timeout
        self.source_tag = source_tag
        self.extra_args = extra_args or []

    def chat(self, message: str) -> str | None:
        """
        Send a message to Hermes and return the text reply.

        Args:
            message: The user's message text.

        Returns:
            The agent's reply text, or None on error.
        """
        cmd = [
            self.hermes_bin,
            "chat",
            "-q",
            message,
            "--source",
            self.source_tag,
            "-Q",  # quiet — suppress banner/spinner
        ]
        cmd.extend(self.extra_args)

        try:
            logger.debug("Calling: %s", " ".join(cmd))

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )

            if result.returncode != 0:
                logger.error(
                    "Hermes exited with code %d: %s",
                    result.returncode,
                    result.stderr[:500] if result.stderr else "(no stderr)",
                )
                return self._error_reply(result.returncode, result.stderr)

            reply = result.stdout.strip()
            if not reply:
                logger.warning("Hermes returned empty output")
                return "_(sem resposta)_"

            return reply

        except subprocess.TimeoutExpired:
            logger.error("Hermes timed out after %ds", self.timeout)
            return (
                f"⏱️ Processamento excedeu o limite de {self.timeout}s. "
                "Tente uma pergunta mais curta."
            )

        except FileNotFoundError:
            logger.error("Hermes binary not found at: %s", self.hermes_bin)
            return "❌ Hermes Agent não encontrado. Verifique a instalação."

        except Exception as e:
            logger.error("Unexpected error calling Hermes: %s", e, exc_info=True)
            return f"❌ Erro inesperado: {str(e)[:200]}"

    def _error_reply(self, returncode: int, stderr: str) -> str:
        """Build a user-friendly error message from a failed Hermes call."""
        if returncode == 1:
            return "❌ Erro ao processar mensagem. Verifique os logs."
        elif returncode == 130:
            return "⏱️ Processamento cancelado por timeout."
        else:
            brief = (stderr or "").split("\n")[-1][:200]
            if brief:
                return f"❌ Erro (código {returncode}): {brief}"
            return f"❌ Erro (código {returncode})"
