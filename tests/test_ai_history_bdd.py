"""Executable acceptance scenario for project-local Codex history."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.ai_history_hook import run_hook
from scripts.sync_ai_history import synchronize
from tests.test_ai_history import write_cursor_transcript, write_session


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

            codex_sessions, cursor_sessions, events = synchronize(project, codex_home)

            self.assertEqual((1, 0, 1), (codex_sessions, cursor_sessions, events))
            self.assertTrue((project / ".local/sessions/codex/project.jsonl").is_symlink())
            self.assertFalse((project / ".local/sessions/codex/unrelated.jsonl").exists())
            derived = (project / ".local/derived/AI_CHAT_RAW.md").read_text()
            self.assertIn("[REDACTED: GitHub token]", derived)
            self.assertNotIn("ghp_", derived)
            self.assertNotIn("private reasoning", derived)
            self.assertEqual(canonical_before, project_session.read_bytes())

    def test_end_of_turn_hook_persists_available_platform_history(self) -> None:
        """The shared hook links Cursor history and synchronizes Codex history."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            project.mkdir()
            codex_home = root / "codex"
            codex_session = codex_home / "sessions/codex.jsonl"
            cursor_session = root / "cursor/transcript.jsonl"
            write_session(codex_session, project, "codex message")
            cursor_session.parent.mkdir()
            write_cursor_transcript(cursor_session, "cursor message")

            run_hook(
                {
                    "hook_event_name": "stop",
                    "conversation_id": "conversation-1",
                    "transcript_path": str(cursor_session),
                },
                project,
                codex_home,
            )

            self.assertTrue((project / ".local/sessions/codex/codex.jsonl").is_symlink())
            self.assertTrue(
                (project / ".local/sessions/cursor/cursor-conversation-1.jsonl").is_symlink()
            )
            derived = (project / ".local/derived/AI_CHAT_RAW.md").read_text()
            self.assertIn("codex message", derived)
            self.assertIn("cursor message", derived)
            self.assertNotIn("hidden", derived)


if __name__ == "__main__":
    unittest.main()
