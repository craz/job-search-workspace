"""Compute and verify immutable legacy source fingerprints."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from scripts.migration.types import FileFingerprint, SourceFingerprint


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Return SHA-256 hex digest for one file without loading it fully."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint_file(path: Path) -> FileFingerprint:
    """Capture size, mtime and SHA-256 for one source artifact."""
    stat = path.stat()
    return FileFingerprint(
        path=str(path),
        size=stat.st_size,
        mtime=stat.st_mtime,
        sha256=sha256_file(path),
    )


def build_source_fingerprint(legacy_root: Path) -> SourceFingerprint:
    """Build the approved fingerprint bundle for one legacy root."""
    db_path = legacy_root / "data/job_search.db"
    jsonl_path = legacy_root / "data/vacancy_scores.jsonl"
    return SourceFingerprint(
        job_search_db=fingerprint_file(db_path),
        vacancy_scores_jsonl=fingerprint_file(jsonl_path),
    )


def fingerprint_to_dict(fingerprint: SourceFingerprint) -> dict[str, object]:
    """Serialize fingerprints for JSON reports."""
    return {
        "job_search_db": {
            "path": fingerprint.job_search_db.path,
            "size": fingerprint.job_search_db.size,
            "mtime": fingerprint.job_search_db.mtime,
            "sha256": fingerprint.job_search_db.sha256,
        },
        "vacancy_scores_jsonl": {
            "path": fingerprint.vacancy_scores_jsonl.path,
            "size": fingerprint.vacancy_scores_jsonl.size,
            "sha256": fingerprint.vacancy_scores_jsonl.sha256,
        },
        "captured_at": datetime.now(UTC).isoformat(),
    }


def fingerprints_equal(left: SourceFingerprint, right: SourceFingerprint) -> bool:
    """Return True when both artifact digests still match."""
    return (
        left.job_search_db.sha256 == right.job_search_db.sha256
        and left.job_search_db.size == right.job_search_db.size
        and left.vacancy_scores_jsonl.sha256 == right.vacancy_scores_jsonl.sha256
        and left.vacancy_scores_jsonl.size == right.vacancy_scores_jsonl.size
    )
