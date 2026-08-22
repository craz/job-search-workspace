"""Target PostgreSQL backup helpers for migration APPLY."""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class BackupMetadata:
    """Non-secret metadata recorded in apply reports."""

    path: str
    size: int
    sha256: str
    captured_at: str
    target_identity: dict[str, str | int | None]
    pg_restore_list_exit_code: int


class BackupError(RuntimeError):
    """Backup creation or validation failed."""


def target_identity_from_url(database_url: str) -> dict[str, str | int | None]:
    """Return safe target DB identity fields without credentials."""
    normalized = database_url.replace("postgresql+psycopg://", "postgresql://")
    parsed = urlparse(normalized)
    return {
        "scheme": parsed.scheme,
        "host": parsed.hostname,
        "port": parsed.port,
        "database": parsed.path.lstrip("/") if parsed.path else None,
        "user": parsed.username,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def create_target_backup(
    *,
    workspace_root: Path,
    run_dir: Path,
    database_url: str,
) -> BackupMetadata:
    """Create and validate a custom-format PostgreSQL dump before APPLY."""
    if database_url.startswith("sqlite"):
        raise BackupError("sqlite targets do not support pg_dump backup")

    dump_path = run_dir / "target-pre-apply.dump"
    compose_cmd = [
        "docker",
        "compose",
        "exec",
        "-T",
        "postgres",
        "pg_dump",
        "-U",
        "job_search",
        "-d",
        "job_search",
        "-Fc",
    ]
    with dump_path.open("wb") as handle:
        completed = subprocess.run(
            compose_cmd,
            cwd=workspace_root,
            check=False,
            stdout=handle,
            stderr=subprocess.PIPE,
        )
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace")
        raise BackupError(f"pg_dump failed with exit code {completed.returncode}: {stderr.strip()}")

    size = dump_path.stat().st_size
    if size <= 0:
        raise BackupError("backup dump is empty")

    with dump_path.open("rb") as dump_handle:
        list_completed = subprocess.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "postgres",
                "pg_restore",
                "--list",
            ],
            cwd=workspace_root,
            check=False,
            stdin=dump_handle,
            capture_output=True,
        )
    if list_completed.returncode != 0:
        stderr = list_completed.stderr.decode("utf-8", errors="replace")
        raise BackupError(
            f"pg_restore --list failed with exit code {list_completed.returncode}: "
            f"{stderr.strip()}"
        )

    return BackupMetadata(
        path=str(dump_path),
        size=size,
        sha256=sha256_file(dump_path),
        captured_at=datetime.now(UTC).isoformat(),
        target_identity=target_identity_from_url(database_url),
        pg_restore_list_exit_code=list_completed.returncode,
    )
