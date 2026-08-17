"""Unit tests for safe, project-bounded Codex history synchronization."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from scripts.ai_history_hook import link_cursor_transcript, run_hook
from scripts.sync_ai_history import synchronize


def write_session(path: Path, cwd: Path, text: str) -> None:
    """Create a minimal synthetic Codex JSONL export for one test."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {"type": "session_meta", "timestamp": "2026-01-01T00:00:00Z", "payload": {"cwd": str(cwd)}},
        {
            "type": "response_item",
            "timestamp": "2026-01-01T00:00:01Z",
            "payload": {"type": "message", "role": "user", "content": [{"text": text}]},
        },
        {
            "type": "response_item",
            "timestamp": "2026-01-01T00:00:02Z",
            "payload": {"type": "reasoning", "summary": [{"text": "private reasoning"}]},
        },
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n{partial")


class AiHistorySynchronizationTests(unittest.TestCase):
    """Protect project scope, canonical files, privacy and idempotency."""

    def test_links_only_matching_sessions_and_builds_redacted_view(self) -> None:
        """Foreign sessions and hidden reasoning never enter project history."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            project.mkdir()
            codex_home = root / "codex"
            matching = codex_home / "sessions/2026/01/matching.jsonl"
            foreign = codex_home / "sessions/2026/01/foreign.jsonl"
            write_session(matching, project, "token ghp_abcdefghijklmnopqrstuvwxyz123456")
            write_session(foreign, root / "other", "foreign private message")

            sessions, events = synchronize(project, codex_home)

            self.assertEqual((1, 1), (sessions, events))
            link = project / ".local/sessions/codex/matching.jsonl"
            self.assertTrue(link.is_symlink())
            self.assertEqual(matching.resolve(), link.resolve())
            derived = (project / ".local/derived/AI_CHAT_RAW.md").read_text()
            self.assertIn("[REDACTED: GitHub token]", derived)
            self.assertNotIn("ghp_", derived)
            self.assertNotIn("private reasoning", derived)
            self.assertNotIn("foreign private message", derived)

    def test_is_idempotent_and_preserves_canonical_bytes(self) -> None:
        """Repeated synchronization never modifies platform-owned JSONL."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            project.mkdir()
            codex_home = root / "codex"
            source = codex_home / "sessions/session.jsonl"
            write_session(source, project, "hello")
            original = source.read_bytes()

            self.assertEqual(synchronize(project, codex_home), synchronize(project, codex_home))
            self.assertEqual(original, source.read_bytes())

    def test_refuses_to_replace_conflicting_project_file(self) -> None:
        """A name collision fails instead of overwriting user data."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            project.mkdir()
            codex_home = root / "codex"
            source = codex_home / "sessions/session.jsonl"
            write_session(source, project, "hello")
            collision = project / ".local/sessions/codex/session.jsonl"
            collision.parent.mkdir(parents=True)
            collision.write_text("user-owned")

            with self.assertRaisesRegex(RuntimeError, "refusing to replace"):
                synchronize(project, codex_home)

    def test_cursor_stop_links_platform_transcript(self) -> None:
        """Cursor's supplied canonical transcript becomes project-local by link."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            project.mkdir()
            transcript = root / "cursor-platform/transcript.jsonl"
            transcript.parent.mkdir()
            transcript.write_text('{"role":"user","text":"synthetic"}\n')
            request = {
                "hook_event_name": "stop",
                "conversation_id": "conversation/one",
                "transcript_path": str(transcript),
            }

            destination = link_cursor_transcript(request, project)

            self.assertIsNotNone(destination)
            assert destination is not None
            self.assertTrue(destination.is_symlink())
            self.assertTrue(os.path.samefile(destination, transcript))

    def test_codex_stop_does_not_treat_its_path_as_cursor_history(self) -> None:
        """PascalCase Codex Stop input cannot create a Cursor transcript link."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            project.mkdir()
            transcript = root / "codex.jsonl"
            transcript.write_text("{}\n")

            destination = link_cursor_transcript(
                {"hook_event_name": "Stop", "transcript_path": str(transcript)},
                project,
            )

            self.assertIsNone(destination)
            self.assertFalse((project / ".local/sessions/cursor").exists())

    def test_shared_hook_runs_with_missing_cursor_transcript(self) -> None:
        """Disabled Cursor transcripts do not prevent Codex synchronization."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            project.mkdir()
            codex_home = root / "codex"
            source = codex_home / "sessions/session.jsonl"
            write_session(source, project, "hello")

            run_hook({"hook_event_name": "stop", "transcript_path": None}, project, codex_home)

            self.assertTrue((project / ".local/sessions/codex/session.jsonl").is_symlink())


if __name__ == "__main__":
    unittest.main()
