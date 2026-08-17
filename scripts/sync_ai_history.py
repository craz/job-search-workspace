"""Synchronize project-local links and a safe view of AI session history.

Codex owns canonical JSONL files under its data home. This module finds sessions
whose recorded working directory is this repository, creates non-destructive
links in ``.local/sessions/codex``, and combines them with Cursor transcripts
already linked by the end-of-turn hook. It atomically rebuilds one derived
Markdown view, performs no network operations, never modifies platform exports,
and excludes reasoning plus system/developer messages. Malformed or concurrently
incomplete JSONL lines are ignored so active sessions are safe to synchronize.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from itertools import chain
from pathlib import Path
from typing import Iterator


REDACTIONS = (
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"), "[REDACTED: GitHub token]"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "[REDACTED: GitHub token]"),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{16,}"), "Bearer [REDACTED: token]"),
    (
        re.compile(
            r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|password)"
            r"(\s*[=:]\s*)[^\s,;\"']+"
        ),
        r"\1\2[REDACTED]",
    ),
)


def redact(value: object) -> str:
    """Return printable text with known credential formats removed."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    for pattern, replacement in REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def json_objects(path: Path) -> Iterator[dict]:
    """Yield valid objects while tolerating a partial active-session tail."""
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                yield value


def session_cwd(path: Path) -> Path | None:
    """Read the first working directory declared by session metadata."""
    for item in json_objects(path):
        if item.get("type") == "session_meta":
            cwd = item.get("payload", {}).get("cwd")
            return Path(cwd).resolve() if isinstance(cwd, str) else None
    return None


def discover_sessions(codex_home: Path, project_root: Path) -> list[Path]:
    """Find canonical sessions explicitly associated with this project."""
    sessions_root = codex_home / "sessions"
    if not sessions_root.is_dir():
        return []
    project_root = project_root.resolve()
    return sorted(
        path.resolve()
        for path in sessions_root.rglob("*.jsonl")
        if session_cwd(path) == project_root
    )


def link_sessions(sources: list[Path], destination: Path) -> list[Path]:
    """Create stable links without replacing an unrelated existing entry."""
    destination.mkdir(parents=True, exist_ok=True)
    links = []
    for source in sources:
        link = destination / source.name
        if link.is_symlink():
            if link.resolve() != source:
                raise RuntimeError(f"refusing to replace conflicting link: {link}")
        elif link.exists():
            if not os.path.samefile(link, source):
                raise RuntimeError(f"refusing to replace existing file: {link}")
        else:
            link.symlink_to(source)
        links.append(link)
    return links


def message_text(payload: dict) -> str:
    """Join visible text parts from one response message."""
    return "\n".join(
        item["text"]
        for item in payload.get("content") or []
        if isinstance(item, dict) and isinstance(item.get("text"), str)
    )


def codex_derived_blocks(source: Path) -> Iterator[tuple[str, str]]:
    """Convert visible Codex response items into timestamped Markdown blocks."""
    for item in json_objects(source):
        if item.get("type") != "response_item":
            continue
        payload = item.get("payload") or {}
        kind = payload.get("type")
        timestamp = str(item.get("timestamp", "unknown-time"))
        if kind == "message" and payload.get("role") in {"user", "assistant"}:
            text = message_text(payload)
            if not text:
                continue
            role = "User" if payload["role"] == "user" else "Assistant"
            phase = payload.get("phase")
            suffix = f" [{phase}]" if phase else ""
            yield timestamp, f"## {timestamp} — {role}{suffix}\n\n{redact(text)}\n"
        elif kind in {"custom_tool_call", "function_call"}:
            value = payload.get("input") if kind == "custom_tool_call" else payload.get("arguments")
            yield timestamp, (
                f"## {timestamp} — Tool Call\n\n"
                f"- Tool: `{payload.get('name', 'unknown')}`\n"
                f"- Call ID: `{payload.get('call_id', 'unknown')}`\n\n"
                f"```text\n{redact(value or '')}\n```\n"
            )
        elif kind in {"custom_tool_call_output", "function_call_output"}:
            yield timestamp, (
                f"## {timestamp} — Tool Output\n\n"
                f"- Call ID: `{payload.get('call_id', 'unknown')}`\n\n"
                f"```text\n{redact(payload.get('output') or '')}\n```\n"
            )


def cursor_derived_blocks(source: Path) -> Iterator[tuple[str, str]]:
    """Convert visible Cursor transcript messages and tool calls into Markdown.

    Cursor transcripts currently contain ordered rows without timestamps. Their
    source path and row number provide a deterministic sort key. Only explicit
    user and assistant roles are accepted; other roles and lifecycle rows are
    ignored. Unknown content item types are skipped instead of serialized.
    """
    source_key = str(source.resolve())
    for row_number, item in enumerate(json_objects(source)):
        role = item.get("role")
        message = item.get("message")
        if role not in {"user", "assistant"} or not isinstance(message, dict):
            continue
        label = "User" if role == "user" else "Assistant"
        for content_number, content in enumerate(message.get("content") or []):
            if not isinstance(content, dict):
                continue
            kind = content.get("type")
            sort_key = f"cursor:{source_key}:{row_number:08d}:{content_number:08d}"
            if kind == "text" and isinstance(content.get("text"), str):
                text = content["text"]
                if text:
                    yield sort_key, f"## Cursor — {label}\n\n{redact(text)}\n"
            elif kind == "tool_use" and isinstance(content.get("name"), str):
                yield sort_key, (
                    "## Cursor — Tool Call\n\n"
                    f"- Tool: `{content['name']}`\n\n"
                    f"```text\n{redact(content.get('input') or '')}\n```\n"
                )


def rebuild_derived(codex_sources: list[Path], cursor_sources: list[Path], target: Path) -> int:
    """Atomically combine safe Codex and Cursor events and return their count."""
    events = sorted(
        chain(
            (
                event
                for source in codex_sources
                for event in codex_derived_blocks(source)
            ),
            (
                event
                for source in cursor_sources
                for event in cursor_derived_blocks(source)
            ),
        ),
        key=lambda event: event[0],
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# Raw operational trace AI-сессий\n\n"
        "Приватное производное представление доступных сообщений, tool calls и "
        "tool outputs. Скрытые reasoning-блоки и system/developer-инструкции "
        "исключены. Чувствительные значения редактируются.\n\n"
        "Canonical sources: `.local/sessions/codex/*.jsonl` and "
        "`.local/sessions/cursor/*.jsonl`.\n\n"
    )
    descriptor, temporary_name = tempfile.mkstemp(
        dir=target.parent, prefix=f".{target.name}.", suffix=".tmp", text=True
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(header)
            stream.write("\n".join(block for _, block in events))
        Path(temporary_name).replace(target)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise
    return len(events)


def synchronize(project_root: Path, codex_home: Path) -> tuple[int, int, int]:
    """Synchronize Codex links and rebuild the view from both supported agents."""
    local = project_root / ".local"
    sources = discover_sessions(codex_home, project_root)
    links = link_sessions(sources, local / "sessions" / "codex")
    cursor_directory = local / "sessions" / "cursor"
    cursor_sources = sorted(cursor_directory.glob("*.jsonl")) if cursor_directory.is_dir() else []
    events = rebuild_derived(
        links,
        cursor_sources,
        local / "derived" / "AI_CHAT_RAW.md",
    )
    return len(links), len(cursor_sources), events


def parse_args() -> argparse.Namespace:
    """Parse explicit roots, with safe defaults based on script location."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")),
    )
    return parser.parse_args()


def main() -> None:
    """Run synchronization and print counts without session content."""
    args = parse_args()
    codex_sessions, cursor_sessions, events = synchronize(
        args.project_root.resolve(), args.codex_home.resolve()
    )
    print(
        "AI history synchronized: "
        f"codex_sessions={codex_sessions} cursor_sessions={cursor_sessions} events={events}"
    )


if __name__ == "__main__":
    main()
