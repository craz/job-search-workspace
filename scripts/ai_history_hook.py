#!/usr/bin/env python3
"""Fail-open end-of-turn hook shared by Codex and Cursor.

The hook consumes lifecycle JSON from standard input, links a Cursor-owned
transcript when Cursor provides ``transcript_path``, and invokes the existing
Codex history synchronizer. It always returns an empty JSON object on standard
output because both products require structured hook output. Failures are
reported without private content on standard error and never block completion
of the user's agent turn.

The script performs no network calls and never modifies platform transcripts.
Cursor paths are accepted only for the lowercase Cursor ``stop`` event, must be
regular files, and are linked under the ignored project-local history tree.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.sync_ai_history import synchronize


SAFE_ID = re.compile(r"[^A-Za-z0-9._-]+")


def read_hook_input() -> dict:
    """Parse one hook request, returning an empty request for invalid input."""
    try:
        value = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def cursor_transcript_source(request: dict) -> Path | None:
    """Return Cursor's existing transcript only for a genuine Cursor stop event."""
    if request.get("hook_event_name") != "stop":
        return None
    raw_path = request.get("transcript_path")
    if not isinstance(raw_path, str) or not raw_path:
        return None
    source = Path(raw_path).expanduser().resolve()
    return source if source.is_file() else None


def link_cursor_transcript(request: dict, project_root: Path) -> Path | None:
    """Link a Cursor transcript without replacing any unrelated local file."""
    source = cursor_transcript_source(request)
    if source is None:
        return None
    conversation = request.get("conversation_id")
    safe_conversation = SAFE_ID.sub("-", str(conversation or source.stem)).strip("-.")
    if not safe_conversation:
        safe_conversation = "unknown-conversation"
    suffix = source.suffix if source.suffix else ".jsonl"
    destination_dir = project_root / ".local" / "sessions" / "cursor"
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"cursor-{safe_conversation}{suffix}"
    if destination.is_symlink():
        if destination.resolve() != source:
            raise RuntimeError("refusing to replace a conflicting Cursor transcript link")
    elif destination.exists():
        if not os.path.samefile(destination, source):
            raise RuntimeError("refusing to replace an existing Cursor transcript file")
    else:
        destination.symlink_to(source)
    return destination


def run_hook(request: dict, project_root: Path, codex_home: Path) -> None:
    """Apply all end-of-turn persistence operations without producing content."""
    link_cursor_transcript(request, project_root)
    synchronize(project_root, codex_home)


def main() -> int:
    """Run fail-open synchronization and emit the required empty JSON response."""
    project_root = Path(__file__).resolve().parent.parent
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).resolve()
    try:
        run_hook(read_hook_input(), project_root, codex_home)
    except Exception as error:  # A history failure must never block an agent turn.
        print(f"AI history hook skipped: {type(error).__name__}", file=sys.stderr)
    print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
