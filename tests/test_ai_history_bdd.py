"""Executable acceptance scenario for project-local Codex history."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.sync_ai_history import synchronize
from tests.test_ai_history import write_session


class AiHistoryScenarios(unittest.TestCase):
    """Bind the scenario in ``tests/features/ai_history.feature``."""

    def test_active_project_session_is_synchronized_safely(self) -> None:
        """Link only project history while preserving and sanitizing raw data."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            project.mkdir()
            codex_home = root / "codex"
            project_session = codex_home / "sessions/project.jsonl"
            unrelated_session = codex_home / "sessions/unrelated.jsonl"
            write_session(
                project_session,
                project,
                "credential ghp_abcdefghijklmnopqrstuvwxyz123456",
            )
            write_session(unrelated_session, root / "unrelated", "unrelated")
            canonical_before = project_session.read_bytes()

            sessions, events = synchronize(project, codex_home)

            self.assertEqual((1, 1), (sessions, events))
            self.assertTrue((project / ".local/sessions/codex/project.jsonl").is_symlink())
            self.assertFalse((project / ".local/sessions/codex/unrelated.jsonl").exists())
            derived = (project / ".local/derived/AI_CHAT_RAW.md").read_text()
            self.assertIn("[REDACTED: GitHub token]", derived)
            self.assertNotIn("ghp_", derived)
            self.assertNotIn("private reasoning", derived)
            self.assertEqual(canonical_before, project_session.read_bytes())


if __name__ == "__main__":
    unittest.main()
