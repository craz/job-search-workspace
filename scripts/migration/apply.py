"""Orchestrate backup + first supported legacy migration APPLY."""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from scripts.migration.apply_writer import ApplyWriteError, apply_planned_records
from scripts.migration.backup import BackupError, BackupMetadata, create_target_backup
from scripts.migration.constants import (
    DEFAULT_LEGACY_ROOT,
    EXPECTED_PLANNED_INSERTS_TOTAL,
    MODE_APPLY,
    PROMPT_VERSION_SENTINEL,
)
from scripts.migration.dry_run import discover_default_target_url
from scripts.migration.fingerprint import (
    build_source_fingerprint,
    fingerprint_to_dict,
    fingerprints_equal,
)
from scripts.migration.plan import build_plan
from scripts.migration.preflight import (
    PreflightError,
    assert_live_plan_matches_dry_run,
    validate_dry_run_artifact,
)
from scripts.migration.report import write_json_report
from scripts.migration.source_reader import load_legacy_snapshot
from scripts.migration.target_inspect import target_row_counts
from scripts.migration.transform import transform_snapshot
from scripts.migration.types import LegacyAnomaly, Severity, ValidationIssue
from scripts.migration.validation import collect_validation_issues
from scripts.migration.verify import VerificationError, run_post_apply_verification
from scripts.migration.versions import resolve_versions


@contextmanager
def writable_target_session(database_url: str) -> Iterator[Session]:
    """Open one writable SQLAlchemy session; caller owns commit/rollback."""
    engine = create_engine(database_url, pool_pre_ping=True)
    if database_url.startswith("sqlite"):
        from job_search_core.models import Base

        Base.metadata.create_all(engine)
    session = Session(bind=engine, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _apply_counters_to_entity_counts(counters: dict[str, object]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for entity, counter in counters.items():
        result[entity] = {
            "inserted": counter.inserted,
            "existing_equivalent": counter.existing_equivalent,
            "conflict": counter.conflict,
        }
    return result


def _render_apply_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Migration apply report",
        "",
        f"- **Run ID:** `{report['run_id']}`",
        f"- **Mode:** `{report['mode']}`",
        f"- **Result:** {'PASS' if report['success'] else 'FAIL'}",
        f"- **Dry-run bound to:** `{report['dry_run_id']}`",
        f"- **Transaction:** `{report['transaction_result']}`",
        "",
        "## Applied counts",
        "",
        "| Entity | Inserted | Existing equivalent | Conflict |",
        "|---|---:|---:|---:|",
    ]
    for entity, values in (report.get("applied") or {}).items():
        lines.append(
            f"| {entity} | {values['inserted']} | {values['existing_equivalent']} | {values['conflict']} |"
        )
    backup = report.get("target_backup") or {}
    if backup:
        lines.extend(
            [
                "",
                "## Target backup",
                "",
                f"- Path: `{backup.get('path')}`",
                f"- Size: `{backup.get('size')}`",
                f"- SHA-256: `{backup.get('sha256')}`",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def run_apply(
    *,
    workspace_root: Path,
    dry_run_id: str,
    legacy_root: Path = DEFAULT_LEGACY_ROOT,
    target_database_url: str | None = None,
    output_root: Path | None = None,
    skip_backup: bool = False,
) -> tuple[Path, bool]:
    """Execute one bounded APPLY bound to a verified dry-run artifact."""
    started_at = datetime.now(UTC)
    artifact_root = output_root or workspace_root / "backups/migration-runs"
    run_dir = artifact_root / dry_run_id
    if not run_dir.exists():
        raise PreflightError(f"run directory not found: {run_dir}")

    dry_run_report = validate_dry_run_artifact(
        run_dir=run_dir,
        legacy_root=legacy_root,
        workspace_root=workspace_root,
    )
    mapping_version, importer_version = resolve_versions(workspace_root)
    target_url = target_database_url or discover_default_target_url()
    if not target_url:
        raise PreflightError("target database URL is required")

    fingerprint_start = build_source_fingerprint(legacy_root)
    fingerprint_dict = fingerprint_to_dict(fingerprint_start)

    snapshot = load_legacy_snapshot(legacy_root)
    anomalies: list[LegacyAnomaly] = []
    planned = transform_snapshot(snapshot, anomalies=anomalies)
    validation_issues = collect_validation_issues(snapshot, planned)

    backup_meta: BackupMetadata | None = None
    if not skip_backup:
        if target_url.startswith("sqlite"):
            raise BackupError("backup required for APPLY; sqlite test mode must skip explicitly in tests")
        backup_meta = create_target_backup(
            workspace_root=workspace_root,
            run_dir=run_dir,
            database_url=target_url,
        )

    counts_before: dict[str, int] = {}
    counts_after: dict[str, int] = {}
    applied_counters: dict[str, object] = {}
    entity_counts = {}
    operations: list = []
    transaction_result = "not_started"
    apply_success = False
    verification_issues: list[ValidationIssue] = []

    try:
        with writable_target_session(target_url) as session:
            counts_before = target_row_counts(session)
            operations, entity_counts = build_plan(snapshot, planned, session)
            live_ops: dict[str, int] = {}
            for operation in operations:
                live_ops[operation.action.value] = live_ops.get(operation.action.value, 0) + 1
            assert_live_plan_matches_dry_run(
                dry_run_report=dry_run_report,
                live_counts={entity: counter.to_dict() for entity, counter in entity_counts.items()},
                live_operations_summary=live_ops,
            )

            fatal_validation = [issue for issue in validation_issues if issue.severity is Severity.FATAL]
            if fatal_validation:
                raise PreflightError(f"live validation failed: {fatal_validation[0].message}")

            applied_counters = apply_planned_records(session, planned, run_id=dry_run_id)

            inserted_total = sum(counter.inserted for counter in applied_counters.values())
            if inserted_total != EXPECTED_PLANNED_INSERTS_TOTAL:
                raise ApplyWriteError(
                    f"pre-commit inserted total {inserted_total} != expected {EXPECTED_PLANNED_INSERTS_TOTAL}"
                )

            fingerprint_pre_commit = build_source_fingerprint(legacy_root)
            if not fingerprints_equal(fingerprint_start, fingerprint_pre_commit):
                raise PreflightError("source fingerprint changed before commit")

            session.commit()
            transaction_result = "committed"
            counts_after = target_row_counts(session)

        with writable_target_session(target_url) as session:
            inserted_by_entity = {entity: counter.inserted for entity, counter in applied_counters.items()}
            verification_issues = run_post_apply_verification(
                session,
                legacy_root=legacy_root,
                planned=planned,
                counts_before=counts_before,
                counts_after=counts_after,
                inserted=inserted_by_entity,
            )
            if any(issue.severity is Severity.FATAL for issue in verification_issues):
                raise VerificationError(verification_issues[0].message)
            apply_success = True
    except (PreflightError, BackupError, ApplyWriteError) as exc:
        transaction_result = "rolled_back"
        validation_issues.append(
            ValidationIssue(Severity.FATAL, "apply_failed", str(exc))
        )
        apply_success = False
    except VerificationError as exc:
        validation_issues.append(
            ValidationIssue(Severity.FATAL, "verification_failed", str(exc))
        )
        apply_success = False

    finished_at = datetime.now(UTC)
    applied = _apply_counters_to_entity_counts(applied_counters)
    report_payload = {
        "run_id": dry_run_id,
        "dry_run_id": dry_run_id,
        "mode": MODE_APPLY,
        "source": str(legacy_root),
        "source_fingerprint": fingerprint_dict,
        "mapping_version": mapping_version,
        "importer_version": importer_version,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "committed_at": finished_at.isoformat() if transaction_result == "committed" else None,
        "success": apply_success,
        "transaction_result": transaction_result,
        "target_counts_before": counts_before,
        "target_counts_after": counts_after,
        "applied": applied,
        "counts": {entity: counter.to_dict() for entity, counter in entity_counts.items()},
        "operations_summary": dry_run_report.get("operations_summary"),
        "validation_errors": [
            {"severity": issue.severity.value, "code": issue.code, "message": issue.message}
            for issue in validation_issues
            if issue.severity is Severity.FATAL
        ],
        "verification_errors": [
            {"severity": issue.severity.value, "code": issue.code, "message": issue.message}
            for issue in verification_issues
            if issue.severity is Severity.FATAL
        ],
        "legacy_anomalies": dry_run_report.get("legacy_anomalies") or [],
        "deferred_summary": dry_run_report.get("deferred_summary") or {},
        "target_backup": (
            {
                "path": backup_meta.path,
                "size": backup_meta.size,
                "sha256": backup_meta.sha256,
                "captured_at": backup_meta.captured_at,
                "target_identity": backup_meta.target_identity,
                "pg_restore_list_exit_code": backup_meta.pg_restore_list_exit_code,
            }
            if backup_meta
            else None
        ),
        "notes": [
            f'prompt_version sentinel `{PROMPT_VERSION_SENTINEL}` marks migration provenance only.',
            "Restore runbook: docs/DATA_MIGRATION.md §27.1",
        ],
    }

    write_json_report(run_dir / "apply-report.json", _ApplyReportAdapter(report_payload))
    (run_dir / "apply-report.md").write_text(_render_apply_markdown(report_payload), encoding="utf-8")
    return run_dir, apply_success


class _ApplyReportAdapter:
    """Adapt apply dict payload to report writer interface."""

    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def to_dict(self) -> dict[str, object]:
        return self._payload

    @property
    def success(self) -> bool:
        return bool(self._payload.get("success"))
