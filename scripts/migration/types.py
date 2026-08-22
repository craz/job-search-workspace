"""Shared datatypes for legacy migration dry-run planning."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any


class PlanAction(StrEnum):
    """High-level migration operation outcome for one source record."""

    PLANNED_INSERT = "PLANNED_INSERT"
    EXISTING_EQUIVALENT = "EXISTING_EQUIVALENT"
    CONFLICT = "CONFLICT"
    DEFERRED = "DEFERRED"
    SKIPPED = "SKIPPED"


class Severity(StrEnum):
    """Validation and anomaly severity."""

    FATAL = "FATAL"
    WARNING = "WARNING"


@dataclass(frozen=True, slots=True)
class SourceIdentity:
    """Stable legacy identity independent of target UUID."""

    entity_type: str
    source: str | None
    external_id: str
    legacy_key: str | None = None


@dataclass(frozen=True, slots=True)
class ParentIdentity:
    """Resolved parent reference by source identity, not UUID."""

    entity_type: str
    source: str
    external_id: str


@dataclass(frozen=True, slots=True)
class FileFingerprint:
    """Immutable file fingerprint used for source integrity gates."""

    path: str
    size: int
    mtime: float | None
    sha256: str


@dataclass(frozen=True, slots=True)
class SourceFingerprint:
    """Fingerprint bundle captured at dry-run start and end."""

    job_search_db: FileFingerprint
    vacancy_scores_jsonl: FileFingerprint


@dataclass(slots=True)
class ValidationIssue:
    """Structured validation, warning, or fatal issue."""

    severity: Severity
    code: str
    message: str
    entity_type: str | None = None
    legacy_key: str | None = None


@dataclass(slots=True)
class LegacyAnomaly:
    """Known legacy data anomaly preserved in migration semantics."""

    code: str
    entity_type: str
    legacy_key: str
    message: str


@dataclass(slots=True)
class PlannedRecord:
    """Normalized target payload for one eligible legacy row."""

    entity_type: str
    identity: SourceIdentity
    payload: dict[str, Any]
    parent: ParentIdentity | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MigrationOperation:
    """One row in the migration plan."""

    entity_type: str
    action: PlanAction
    source_identity: SourceIdentity
    parent_identity: ParentIdentity | None = None
    reason: str = ""
    warnings: list[str] = field(default_factory=list)
    target_id: str | None = None


@dataclass(slots=True)
class EntityCounts:
    """Per-entity dry-run counters."""

    source: int = 0
    eligible: int = 0
    planned_insert: int = 0
    existing_equivalent: int = 0
    conflict: int = 0
    deferred: int = 0
    skipped: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "source": self.source,
            "eligible": self.eligible,
            "planned_insert": self.planned_insert,
            "existing_equivalent": self.existing_equivalent,
            "conflict": self.conflict,
            "deferred": self.deferred,
            "skipped": self.skipped,
        }


@dataclass(slots=True)
class DryRunReport:
    """Machine-readable dry-run result."""

    run_id: str
    mode: str
    source: str
    source_fingerprint: dict[str, Any]
    mapping_version: str
    importer_version: str
    started_at: datetime
    finished_at: datetime
    success: bool
    counts: dict[str, dict[str, int]]
    validation_errors: list[dict[str, str]]
    warnings: list[dict[str, str]]
    legacy_anomalies: list[dict[str, str]]
    deferred_summary: dict[str, Any]
    operations_summary: dict[str, int]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "mode": self.mode,
            "source": self.source,
            "source_fingerprint": self.source_fingerprint,
            "mapping_version": self.mapping_version,
            "importer_version": self.importer_version,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "success": self.success,
            "counts": self.counts,
            "validation_errors": self.validation_errors,
            "warnings": self.warnings,
            "legacy_anomalies": self.legacy_anomalies,
            "deferred_summary": self.deferred_summary,
            "operations_summary": self.operations_summary,
            "notes": self.notes,
        }


@dataclass(slots=True)
class LegacySnapshot:
    """Approved and deferred legacy datasets loaded read-only from source."""

    companies: list[dict[str, Any]]
    watch_only_companies: list[dict[str, Any]]
    vacancies: list[dict[str, Any]]
    orphan_vacancies: list[dict[str, Any]]
    applications: list[dict[str, Any]]
    people: list[dict[str, Any]]
    daily_metrics: list[dict[str, Any]]
    hypotheses: list[dict[str, Any]]
    scoring_rows: list[dict[str, Any]]
    scoring_deferred_off_db: list[dict[str, Any]]
    scoring_deferred_history: list[dict[str, Any]]
    scoring_deferred_orphan: list[dict[str, Any]]
    embedded_assessment_vacancy_ids: list[int]
    hh_vacancy_ids: set[str]
    source_counts: dict[str, int]
    deferred_counts: dict[str, int]
