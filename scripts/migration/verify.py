"""Post-APPLY verification against the migration contract."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from job_search_core.models import (
    Assessment,
    Company,
    DailyMetric,
    Hypothesis,
    Person,
    Vacancy,
)

from scripts.migration.constants import EXPECTED_ELIGIBLE_COUNTS
from scripts.migration.source_reader import load_legacy_snapshot
from scripts.migration.target_inspect import fetch_existing_payload
from scripts.migration.transform import company_identity, vacancy_identity
from scripts.migration.types import PlannedRecord, ValidationIssue, Severity


class VerificationError(RuntimeError):
    """Post-APPLY verification failed."""


def verify_target_count_deltas(
    *,
    before: dict[str, int],
    after: dict[str, int],
    inserted: dict[str, int],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for entity, expected_delta in EXPECTED_ELIGIBLE_COUNTS.items():
        actual_delta = after[entity] - before[entity]
        if actual_delta != inserted.get(entity, 0):
            issues.append(
                ValidationIssue(
                    Severity.FATAL,
                    "insert_count_mismatch",
                    f"{entity}: target delta {actual_delta} != applied inserted {inserted.get(entity, 0)}",
                    entity_type=entity,
                )
            )
        if actual_delta != expected_delta:
            issues.append(
                ValidationIssue(
                    Severity.FATAL,
                    "expected_delta_mismatch",
                    f"{entity}: target delta {actual_delta} != expected {expected_delta}",
                    entity_type=entity,
                )
            )
    return issues


def verify_planned_identities_exist(session: Session, planned: dict[str, list[PlannedRecord]]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for entity_type, records in planned.items():
        for record in records:
            existing = fetch_existing_payload(
                session,
                entity_type,
                source=record.identity.source,
                external_id=record.identity.external_id,
            )
            if existing is None:
                issues.append(
                    ValidationIssue(
                        Severity.FATAL,
                        "missing_imported_identity",
                        f"missing ({record.identity.source}, {record.identity.external_id})",
                        entity_type=entity_type,
                        legacy_key=record.identity.legacy_key,
                    )
                )
    return issues


def verify_deferred_absence(session: Session, legacy_root) -> list[ValidationIssue]:
    """Ensure deferred legacy rows were not imported."""
    issues: list[ValidationIssue] = []
    snapshot = load_legacy_snapshot(legacy_root)

    for row in snapshot.vacancies_missing_url:
        identity = vacancy_identity(row)
        existing = fetch_existing_payload(
            session,
            "vacancies",
            source=identity.source,
            external_id=identity.external_id,
        )
        if existing is not None:
            issues.append(
                ValidationIssue(
                    Severity.FATAL,
                    "deferred_vacancy_imported",
                    f"missing-url vacancy {row['id']} was imported",
                    entity_type="vacancies",
                )
            )

    for row in snapshot.orphan_vacancies:
        identity = vacancy_identity(row)
        existing = fetch_existing_payload(
            session,
            "vacancies",
            source=identity.source,
            external_id=identity.external_id,
        )
        if existing is not None:
            issues.append(
                ValidationIssue(
                    Severity.FATAL,
                    "deferred_vacancy_imported",
                    f"orphan vacancy {row['id']} was imported",
                    entity_type="vacancies",
                )
            )

    watch_only_identities = {company_identity(row).external_id for row in snapshot.watch_only_companies}
    imported_watch_only = session.scalar(
        select(func.count())
        .select_from(Company)
        .where(Company.external_id.in_(watch_only_identities))
    )
    if imported_watch_only:
        issues.append(
            ValidationIssue(
                Severity.FATAL,
                "watch_only_company_imported",
                f"found {imported_watch_only} watch-only companies in target",
                entity_type="companies",
            )
        )

    off_db_hh_ids = {
        str((record.get("score") or {}).get("vacancy_id"))
        for record in snapshot.scoring_deferred_off_db
    }
    imported_off_db = session.scalar(
        select(func.count())
        .select_from(Assessment)
        .where(Assessment.external_id.in_(off_db_hh_ids))
    )
    if imported_off_db:
        issues.append(
            ValidationIssue(
                Severity.FATAL,
                "off_db_assessment_imported",
                f"found {imported_off_db} category-B assessments in target",
                entity_type="assessments",
            )
        )

    return issues


def verify_relationship_samples(session: Session, planned: dict[str, list[PlannedRecord]]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    sample_vacancy = planned["vacancies"][0]
    vacancy = session.scalar(
        select(Vacancy).where(
            Vacancy.source == sample_vacancy.identity.source,
            Vacancy.external_id == sample_vacancy.identity.external_id,
        )
    )
    if vacancy is None or vacancy.company is None:
        issues.append(
            ValidationIssue(
                Severity.FATAL,
                "vacancy_company_link_missing",
                "sample vacancy has no company relation",
                entity_type="vacancies",
            )
        )

    sample_application = planned["applications"][0]
    application_row = fetch_existing_payload(
        session,
        "applications",
        source=sample_application.identity.source,
        external_id=sample_application.identity.external_id,
    )
    if application_row is None or not application_row.get("vacancy_external_id"):
        issues.append(
            ValidationIssue(
                Severity.FATAL,
                "application_vacancy_link_missing",
                "sample application has no vacancy relation",
                entity_type="applications",
            )
        )
    return issues


def run_post_apply_verification(
    session: Session,
    *,
    legacy_root,
    planned: dict[str, list[PlannedRecord]],
    counts_before: dict[str, int],
    counts_after: dict[str, int],
    inserted: dict[str, int],
) -> list[ValidationIssue]:
    """Run all post-commit verification checks."""
    issues: list[ValidationIssue] = []
    issues.extend(verify_target_count_deltas(before=counts_before, after=counts_after, inserted=inserted))
    issues.extend(verify_planned_identities_exist(session, planned))
    issues.extend(verify_deferred_absence(session, legacy_root))
    issues.extend(verify_relationship_samples(session, planned))
    return issues
