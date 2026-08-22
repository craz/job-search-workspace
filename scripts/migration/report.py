"""Generate machine-readable and operator Markdown dry-run reports."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.migration.types import DryRunReport, EntityCounts, LegacyAnomaly, MigrationOperation, PlanAction, ValidationIssue


def write_source_fingerprint(path: Path, fingerprint: dict[str, object]) -> None:
    path.write_text(json.dumps(fingerprint, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_json_report(path: Path, report: DryRunReport) -> None:
    path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def render_markdown(report: DryRunReport) -> str:
    lines = [
        "# Migration dry-run report",
        "",
        f"- **Run ID:** `{report.run_id}`",
        f"- **Mode:** `{report.mode}`",
        f"- **Result:** {'PASS' if report.success else 'FAIL'}",
        f"- **Mapping version:** `{report.mapping_version}`",
        f"- **Importer version:** `{report.importer_version}`",
        "",
        "## Source fingerprint",
        "",
        f"- DB SHA-256: `{report.source_fingerprint['job_search_db']['sha256']}`",
        f"- JSONL SHA-256: `{report.source_fingerprint['vacancy_scores_jsonl']['sha256']}`",
        "",
        "## Counts",
        "",
        "| Entity | Eligible | Insert | Equivalent | Conflict | Deferred |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for entity, values in report.counts.items():
        lines.append(
            f"| {entity} | {values['eligible']} | {values['planned_insert']} | "
            f"{values['existing_equivalent']} | {values['conflict']} | {values['deferred']} |"
        )
    lines.extend(["", "## Operations summary", ""])
    for action, count in sorted(report.operations_summary.items()):
        lines.append(f"- `{action}`: {count}")
    if report.legacy_anomalies:
        lines.extend(["", "## Legacy anomalies", ""])
        for item in report.legacy_anomalies:
            lines.append(f"- `{item['code']}` ({item['entity_type']} `{item['legacy_key']}`): {item['message']}")
    if report.validation_errors:
        lines.extend(["", "## Validation errors", ""])
        for item in report.validation_errors:
            lines.append(f"- `{item['code']}`: {item['message']}")
    if report.warnings:
        lines.extend(["", "## Warnings", ""])
        for item in report.warnings:
            lines.append(f"- `{item['code']}`: {item['message']}")
    if report.notes:
        lines.extend(["", "## Notes", ""])
        for note in report.notes:
            lines.append(f"- {note}")
    if not report.success:
        lines.extend(["", "## Blockers for APPLY", "", "- Resolve validation errors and conflicts before DATA-00.5."])
    lines.append("")
    return "\n".join(lines)


def write_markdown_report(path: Path, report: DryRunReport) -> None:
    path.write_text(render_markdown(report), encoding="utf-8")


def build_report(
    *,
    run_id: str,
    mode: str,
    source: str,
    source_fingerprint: dict[str, object],
    mapping_version: str,
    importer_version: str,
    started_at,
    finished_at,
    counts: dict[str, EntityCounts],
    validation_issues: list[ValidationIssue],
    anomalies: list[LegacyAnomaly],
    deferred_summary: dict[str, object],
    operations: list[MigrationOperation],
    notes: list[str],
) -> DryRunReport:
    fatal = [issue for issue in validation_issues if issue.severity.value == "FATAL"]
    conflicts = sum(1 for op in operations if op.action is PlanAction.CONFLICT)
    success = not fatal and conflicts == 0
    operations_summary: dict[str, int] = {}
    for operation in operations:
        operations_summary[operation.action.value] = operations_summary.get(operation.action.value, 0) + 1
    return DryRunReport(
        run_id=run_id,
        mode=mode,
        source=source,
        source_fingerprint=source_fingerprint,
        mapping_version=mapping_version,
        importer_version=importer_version,
        started_at=started_at,
        finished_at=finished_at,
        success=success,
        counts={entity: counter.to_dict() for entity, counter in counts.items()},
        validation_errors=[
            {"severity": issue.severity.value, "code": issue.code, "message": issue.message}
            for issue in validation_issues
            if issue.severity.value == "FATAL"
        ],
        warnings=[
            {"severity": issue.severity.value, "code": issue.code, "message": issue.message}
            for issue in validation_issues
            if issue.severity.value == "WARNING"
        ],
        legacy_anomalies=[
            {
                "code": anomaly.code,
                "entity_type": anomaly.entity_type,
                "legacy_key": anomaly.legacy_key,
                "message": anomaly.message,
            }
            for anomaly in anomalies
        ],
        deferred_summary=deferred_summary,
        operations_summary=operations_summary,
        notes=notes,
    )
