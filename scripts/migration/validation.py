"""Preflight validation for the first supported migration slice."""

from __future__ import annotations

from scripts.migration.constants import EXPECTED_ELIGIBLE_COUNTS, MAX_ELIGIBLE_ASSESSMENTS
from scripts.migration.types import LegacySnapshot, PlannedRecord, Severity, ValidationIssue


def validate_expected_counts(snapshot: LegacySnapshot, planned: dict[str, list[PlannedRecord]]) -> list[ValidationIssue]:
    """Ensure approved source counts still match the locked migration contract."""
    issues: list[ValidationIssue] = []
    actual = {
        "companies": len(planned["companies"]),
        "vacancies": len(planned["vacancies"]),
        "applications": len(planned["applications"]),
        "people": len(planned["people"]),
        "daily_metrics": len(planned["daily_metrics"]),
        "hypotheses": len(planned["hypotheses"]),
        "assessments": len(planned["assessments"]),
    }
    for entity, expected in EXPECTED_ELIGIBLE_COUNTS.items():
        if entity == "assessments":
            if actual[entity] > MAX_ELIGIBLE_ASSESSMENTS:
                issues.append(
                    ValidationIssue(
                        Severity.FATAL,
                        "unexpected_assessment_count",
                        f"expected at most {MAX_ELIGIBLE_ASSESSMENTS}, got {actual[entity]}",
                        entity_type=entity,
                    )
                )
            continue
        if actual[entity] != expected:
            issues.append(
                ValidationIssue(
                    Severity.FATAL,
                    "unexpected_eligible_count",
                    f"expected {expected}, got {actual[entity]}",
                    entity_type=entity,
                )
            )
    if snapshot.source_counts["companies_referenced"] != EXPECTED_ELIGIBLE_COUNTS["companies"]:
        issues.append(
            ValidationIssue(
                Severity.FATAL,
                "unexpected_source_count",
                "referenced company count drifted from contract",
                entity_type="companies",
            )
        )
    return issues


def validate_unique_identities(planned: dict[str, list[PlannedRecord]]) -> list[ValidationIssue]:
    """Detect duplicate planned identities within one entity type."""
    issues: list[ValidationIssue] = []
    for entity_type, records in planned.items():
        seen: set[tuple[str | None, str]] = set()
        for record in records:
            key = (record.identity.source, record.identity.external_id)
            if key in seen:
                issues.append(
                    ValidationIssue(
                        Severity.FATAL,
                        "duplicate_planned_identity",
                        f"duplicate identity {key}",
                        entity_type=entity_type,
                        legacy_key=record.identity.legacy_key,
                    )
                )
            seen.add(key)
    return issues


def validate_parent_resolution(planned: dict[str, list[PlannedRecord]]) -> list[ValidationIssue]:
    """Ensure child rows reference resolvable parent identities inside the slice."""
    issues: list[ValidationIssue] = []
    company_keys = {
        (item.identity.source, item.identity.external_id) for item in planned["companies"]
    }
    vacancy_keys = {
        (item.identity.source, item.identity.external_id) for item in planned["vacancies"]
    }
    for entity_type in ("vacancies", "applications", "people", "assessments"):
        for record in planned[entity_type]:
            if record.parent is None:
                continue
            parent_key = (record.parent.source, record.parent.external_id)
            expected = company_keys if record.parent.entity_type == "companies" else vacancy_keys
            if parent_key not in expected:
                issues.append(
                    ValidationIssue(
                        Severity.FATAL,
                        "missing_parent_identity",
                        f"missing parent {parent_key}",
                        entity_type=entity_type,
                        legacy_key=record.identity.legacy_key,
                    )
                )
    return issues


def collect_validation_issues(
    snapshot: LegacySnapshot,
    planned: dict[str, list[PlannedRecord]],
) -> list[ValidationIssue]:
    """Run all dry-run preflight validators."""
    issues: list[ValidationIssue] = []
    issues.extend(validate_expected_counts(snapshot, planned))
    issues.extend(validate_unique_identities(planned))
    issues.extend(validate_parent_resolution(planned))
    return issues
