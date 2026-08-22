"""Orchestrate a zero-mutation legacy migration dry-run."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

from scripts.migration.constants import DEFAULT_LEGACY_ROOT, MODE_DRY_RUN, PROMPT_VERSION_SENTINEL
from scripts.migration.fingerprint import (
    build_source_fingerprint,
    fingerprint_to_dict,
    fingerprints_equal,
)
from scripts.migration.plan import build_plan
from scripts.migration.report import build_report, write_json_report, write_markdown_report, write_source_fingerprint
from scripts.migration.source_reader import load_legacy_snapshot
from scripts.migration.target_inspect import read_only_target_session, target_row_counts
from scripts.migration.transform import transform_snapshot
from scripts.migration.types import LegacyAnomaly, Severity, ValidationIssue
from scripts.migration.validation import collect_validation_issues
from scripts.migration.versions import resolve_versions


def discover_default_target_url() -> str | None:
    """Resolve PostgreSQL URL from env or the local compose postgres container."""
    import os

    configured = os.getenv("JOB_SEARCH_CORE_DATABASE_URL")
    if configured:
        return configured
    inspect = subprocess.run(
        [
            "docker",
            "inspect",
            "-f",
            "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
            "job_search_ref-postgres-1",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if inspect.returncode != 0 or not inspect.stdout.strip():
        return None
    host = inspect.stdout.strip()
    return f"postgresql+psycopg://job_search:job_search@{host}:5432/job_search"


def make_run_id(workspace_root: Path) -> str:
    """Create one traceable migration run identifier."""
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    short = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=workspace_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return f"migrate-{timestamp}-{short}"


def run_dry_run(
    *,
    workspace_root: Path,
    legacy_root: Path = DEFAULT_LEGACY_ROOT,
    target_database_url: str,
    output_root: Path | None = None,
) -> tuple[Path, dict[str, int], dict[str, int], bool]:
    """Execute one dry-run and return artifact dir plus target counts before/after."""
    started_at = datetime.now(UTC)
    run_id = make_run_id(workspace_root)
    mapping_version, importer_version = resolve_versions(workspace_root)
    artifact_root = output_root or workspace_root / "backups/migration-runs"
    run_dir = artifact_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    fingerprint_start = build_source_fingerprint(legacy_root)
    fingerprint_dict = fingerprint_to_dict(fingerprint_start)
    write_source_fingerprint(run_dir / "source-fingerprint.json", fingerprint_dict)

    snapshot = load_legacy_snapshot(legacy_root)
    anomalies: list[LegacyAnomaly] = []
    planned = transform_snapshot(snapshot, anomalies=anomalies)
    validation_issues = collect_validation_issues(snapshot, planned)

    notes = [
        f'prompt_version sentinel `{PROMPT_VERSION_SENTINEL}` marks migration provenance only, not historical scoring policy.',
    ]

    with read_only_target_session(target_database_url) as session:
        counts_before = target_row_counts(session)
        operations, entity_counts = build_plan(snapshot, planned, session)
        counts_after = target_row_counts(session)

    fingerprint_end = build_source_fingerprint(legacy_root)
    if not fingerprints_equal(fingerprint_start, fingerprint_end):
        validation_issues.append(
            ValidationIssue(
                Severity.FATAL,
                "source_fingerprint_changed",
                "legacy source fingerprint changed during dry-run",
            )
        )

    finished_at = datetime.now(UTC)
    report = build_report(
        run_id=run_id,
        mode=MODE_DRY_RUN,
        source=str(legacy_root),
        source_fingerprint=fingerprint_dict,
        mapping_version=mapping_version,
        importer_version=importer_version,
        started_at=started_at,
        finished_at=finished_at,
        counts=entity_counts,
        validation_issues=validation_issues,
        anomalies=anomalies,
        deferred_summary={
            "counts": snapshot.deferred_counts,
            "watch_only_companies": len(snapshot.watch_only_companies),
            "orphan_vacancies": len(snapshot.orphan_vacancies),
            "vacancies_missing_url": len(snapshot.vacancies_missing_url),
            "embedded_assessments": len(snapshot.embedded_assessment_vacancy_ids),
            "off_db_score_lines": len(snapshot.scoring_deferred_off_db),
            "historical_score_lines": len(snapshot.scoring_deferred_history),
            "orphan_linked_assessments": len(snapshot.scoring_deferred_orphan),
        },
        operations=operations,
        notes=notes,
    )

    write_json_report(run_dir / "dry-run-report.json", report)
    write_markdown_report(run_dir / "dry-run-report.md", report)

    if counts_before != counts_after:
        raise RuntimeError("target mutation detected during dry-run")

    return run_dir, counts_before, counts_after, report.success
