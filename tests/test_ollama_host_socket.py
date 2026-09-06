"""Unit coverage for Ollama host socket Compose override helpers."""

from __future__ import annotations

import io
import unittest
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


if __name__ == "__main__":
    unittest.main()
