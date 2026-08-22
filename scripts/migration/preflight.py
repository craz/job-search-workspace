"""Preflight gates before a mutating migration APPLY."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.migration.constants import (
    EXPECTED_ELIGIBLE_COUNTS,
    EXPECTED_PLANNED_INSERTS_TOTAL,
    LOCKED_SOURCE_FINGERPRINTS,
    MODE_DRY_RUN,
)
from scripts.migration.fingerprint import build_source_fingerprint, fingerprint_to_dict, fingerprints_equal
from scripts.migration.types import Severity, ValidationIssue
from scripts.migration.versions import resolve_versions


class PreflightError(RuntimeError):
    """APPLY refused because a safety gate failed."""


def load_dry_run_report(run_dir: Path) -> dict[str, object]:
    """Load one verified dry-run artifact bundle."""
    report_path = run_dir / "dry-run-report.json"
    fingerprint_path = run_dir / "source-fingerprint.json"
    if not report_path.exists():
        raise PreflightError(f"missing dry-run report: {report_path}")
    if not fingerprint_path.exists():
        raise PreflightError(f"missing source fingerprint: {fingerprint_path}")
    return json.loads(report_path.read_text(encoding="utf-8"))


def _locked_fingerprint_issues(current: dict[str, object]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for key, expected in LOCKED_SOURCE_FINGERPRINTS.items():
        actual = ((current.get(key) or {}) if isinstance(current, dict) else {}).get("sha256")
        if actual != expected:
            issues.append(
                ValidationIssue(
                    Severity.FATAL,
                    "locked_fingerprint_mismatch",
                    f"{key} SHA-256 {actual!r} != locked {expected!r}",
                )
            )
    return issues


def validate_dry_run_artifact(
    *,
    run_dir: Path,
    legacy_root: Path,
    workspace_root: Path,
) -> dict[str, object]:
    """Refuse APPLY unless the dry-run artifact matches current code and locked source."""
    report = load_dry_run_report(run_dir)
    if report.get("mode") != MODE_DRY_RUN:
        raise PreflightError(f"artifact mode must be {MODE_DRY_RUN}, got {report.get('mode')!r}")
    if not report.get("success"):
        raise PreflightError("dry-run report is not successful")

    fingerprint_path = run_dir / "source-fingerprint.json"
    artifact_fingerprint = json.loads(fingerprint_path.read_text(encoding="utf-8"))
    current_fingerprint = fingerprint_to_dict(build_source_fingerprint(legacy_root))
    if artifact_fingerprint["job_search_db"]["sha256"] != current_fingerprint["job_search_db"]["sha256"]:
        raise PreflightError("current source fingerprint differs from dry-run artifact")
    if artifact_fingerprint["vacancy_scores_jsonl"]["sha256"] != current_fingerprint["vacancy_scores_jsonl"]["sha256"]:
        raise PreflightError("current JSONL fingerprint differs from dry-run artifact")
    issues = _locked_fingerprint_issues(current_fingerprint)
    if issues:
        raise PreflightError(issues[0].message)

    mapping_version, importer_version = resolve_versions(workspace_root)
    if report.get("mapping_version") != mapping_version:
        raise PreflightError("mapping_version changed since dry-run; rerun dry-run")
    if report.get("importer_version") != importer_version:
        raise PreflightError("importer_version changed since dry-run; rerun dry-run")

    operations = report.get("operations_summary") or {}
    planned_total = int(operations.get("PLANNED_INSERT", 0))
    if planned_total != EXPECTED_PLANNED_INSERTS_TOTAL:
        raise PreflightError(
            f"expected {EXPECTED_PLANNED_INSERTS_TOTAL} planned inserts, dry-run has {planned_total}"
        )

    counts = report.get("counts") or {}
    for entity, expected in EXPECTED_ELIGIBLE_COUNTS.items():
        entity_counts = counts.get(entity) or {}
        if entity_counts.get("planned_insert") != expected:
            raise PreflightError(
                f"{entity} planned_insert={entity_counts.get('planned_insert')} != expected {expected}"
            )
        if entity_counts.get("conflict", 0) != 0:
            raise PreflightError(f"{entity} dry-run reported conflicts")

    validation_errors = report.get("validation_errors") or []
    if validation_errors:
        raise PreflightError(f"dry-run validation errors present: {len(validation_errors)}")

    return report


def assert_live_plan_matches_dry_run(
    *,
    dry_run_report: dict[str, object],
    live_counts: dict[str, dict[str, int]],
    live_operations_summary: dict[str, int],
) -> None:
    """Ensure a freshly rebuilt plan still matches the verified dry-run artifact."""
    artifact_counts = dry_run_report.get("counts") or {}
    for entity, values in live_counts.items():
        artifact = artifact_counts.get(entity) or {}
        for field in ("eligible", "planned_insert", "existing_equivalent", "conflict"):
            if values.get(field, 0) != artifact.get(field, 0):
                raise PreflightError(
                    f"live plan drift for {entity}.{field}: {values.get(field)} != {artifact.get(field)}"
                )
    artifact_ops = dry_run_report.get("operations_summary") or {}
    for key in ("PLANNED_INSERT", "EXISTING_EQUIVALENT", "CONFLICT"):
        if live_operations_summary.get(key, 0) != artifact_ops.get(key, 0):
            raise PreflightError(
                f"live operations drift for {key}: "
                f"{live_operations_summary.get(key, 0)} != {artifact_ops.get(key, 0)}"
            )
