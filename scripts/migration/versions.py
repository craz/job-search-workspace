"""Resolve git revisions used to bind a migration run to contract and code."""

from __future__ import annotations

import subprocess
from pathlib import Path


def git_revision(repo_root: Path, *, path: Path | None = None, short: bool = False) -> str:
    """Return one git object name for ``repo_root`` or the last commit touching a path."""
    if path is not None:
        command = ["git", "log", "-1", f"--format={'%h' if short else '%H'}", "--", path.as_posix()]
        completed = subprocess.run(
            command,
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()
    command = ["git", "rev-parse"]
    if short:
        command.append("--short")
    command.append("HEAD")
    completed = subprocess.run(
        command,
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def resolve_versions(workspace_root: Path) -> tuple[str, str]:
    """Return mapping contract revision and current importer workspace revision."""
    mapping = git_revision(workspace_root, path=Path("docs/DATA_MIGRATION.md"))
    importer = git_revision(workspace_root)
    return mapping, importer
