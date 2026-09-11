"""Unit coverage for Ollama host socket Compose override helpers."""

from __future__ import annotations

import io
import select as select_mod
import unittest
import unittest.mock
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts import ollama_host_socket


class OllamaHostSocketTests(unittest.TestCase):
    def test_compose_files_prints_override_when_present(self) -> None:
        override = Path("/tmp/job-search-ollama-override-test.yml")
        override.write_text("services: {}\n", encoding="utf-8")
        try:
            with (
                patch.object(ollama_host_socket, "OVERRIDE_FILE", override),
                redirect_stdout(io.StringIO()) as output,
            ):
                code = ollama_host_socket.compose_files()
            self.assertEqual(code, 0)
            self.assertIn(str(override), output.getvalue())
        finally:
            override.unlink(missing_ok=True)

    def test_override_template_points_scoring_at_egress(self) -> None:
        self.assertIn("ollama-egress:11434", ollama_host_socket.OVERRIDE_TEMPLATE)
        self.assertIn("JOB_SEARCH_SCORING_OLLAMA_BASE_URL", ollama_host_socket.OVERRIDE_TEMPLATE)


class OllamaHostSocketRelayTests(unittest.TestCase):
    def test_relay_source_continues_on_idle_select_timeout(self) -> None:
        """Regression: idle select must continue, not break (cold Ollama generate)."""
        source = Path(ollama_host_socket.__file__).read_text(encoding="utf-8")
        self.assertIn("if not readable:", source)
        self.assertIn("continue", source)
        self.assertNotIn("if errored or not readable:\n                break", source)

    def test_relay_continues_after_idle_then_eof(self) -> None:
        client = unittest.mock.MagicMock(name="client")
        upstream = unittest.mock.MagicMock(name="upstream")
        calls = {"n": 0}

        def fake_select(sockets, _w, _e, _timeout):
            calls["n"] += 1
            if calls["n"] == 1:
                return ([], [], [])
            return ([client], [], [])

        client.recv.return_value = b""
        with patch.object(select_mod, "select", side_effect=fake_select):
            ollama_host_socket._relay(client, upstream)
        self.assertGreaterEqual(calls["n"], 2)
        client.recv.assert_called()


if __name__ == "__main__":
    unittest.main()
