"""Build migration plan operations from transformed records and target state."""

from __future__ import annotations

from sqlalchemy.orm import Session

from scripts.migration.target_inspect import compare_with_target
from scripts.migration.types import EntityCounts, LegacySnapshot, MigrationOperation, PlanAction, PlannedRecord, SourceIdentity


def _deferred_operations(snapshot: LegacySnapshot) -> list[MigrationOperation]:
    operations: list[MigrationOperation] = []
    for row in snapshot.watch_only_companies:
        identity = SourceIdentity(
            entity_type="companies",
            source=None,
            external_id=str(row["id"]),
            legacy_key=f"company:{row['id']}",
        )
        operations.append(
            MigrationOperation(
                entity_type="companies",
                action=PlanAction.DEFERRED,
                source_identity=identity,
                reason="watch_only_company",
            )
        )
    for row in snapshot.orphan_vacancies:
        operations.append(
            MigrationOperation(
                entity_type="vacancies",
                action=PlanAction.DEFERRED,
                source_identity=SourceIdentity(
                    entity_type="vacancies",
                    source=None,
                    external_id=str(row["id"]),
                    legacy_key=f"vacancy:{row['id']}",
                ),
                reason="needs_parent_entity",
            )
        )
    for row in snapshot.vacancies_missing_url:
        operations.append(
            MigrationOperation(
                entity_type="vacancies",
                action=PlanAction.DEFERRED,
                source_identity=SourceIdentity(
                    entity_type="vacancies",
                    source=None,
                    external_id=str(row["id"]),
                    legacy_key=f"vacancy:{row['id']}",
                ),
                reason="missing_vacancy_url",
            )
        )
    for vacancy_id in snapshot.embedded_assessment_vacancy_ids:
        operations.append(
            MigrationOperation(
                entity_type="assessments",
                action=PlanAction.DEFERRED,
                source_identity=SourceIdentity(
                    entity_type="assessments",
                    source=None,
                    external_id=str(vacancy_id),
                    legacy_key=f"embedded-assessment:vacancy:{vacancy_id}",
                ),
                reason="embedded_incomplete_assessment",
            )
        )
    for record in snapshot.scoring_deferred_off_db:
        hh_id = str((record.get("score") or {}).get("vacancy_id") or (record.get("vacancy") or {}).get("vacancy_id"))
        operations.append(
            MigrationOperation(
                entity_type="assessments",
                action=PlanAction.DEFERRED,
                source_identity=SourceIdentity(
                    entity_type="assessments",
                    source=None,
                    external_id=hh_id,
                    legacy_key=f"assessment:off-db:{hh_id}",
                ),
                reason="off_db_scoring",
            )
        )
    for record in snapshot.scoring_deferred_orphan:
        hh_id = str((record.get("score") or {}).get("vacancy_id") or (record.get("vacancy") or {}).get("vacancy_id"))
        operations.append(
            MigrationOperation(
                entity_type="assessments",
                action=PlanAction.DEFERRED,
                source_identity=SourceIdentity(
                    entity_type="assessments",
                    source=None,
                    external_id=hh_id,
                    legacy_key=f"assessment:orphan-vacancy:{hh_id}",
                ),
                reason="orphan_vacancy_linked_score",
            )
        )
    for record in snapshot.scoring_deferred_history:
        hh_id = str((record.get("score") or {}).get("vacancy_id") or (record.get("vacancy") or {}).get("vacancy_id"))
        operations.append(
            MigrationOperation(
                entity_type="assessments",
                action=PlanAction.DEFERRED,
                source_identity=SourceIdentity(
                    entity_type="assessments",
                    source=None,
                    external_id=hh_id,
                    legacy_key=f"assessment:history:{hh_id}",
                ),
                reason="historical_scoring_data",
            )
        )
    return operations


def build_plan(
    snapshot: LegacySnapshot,
    planned: dict[str, list[PlannedRecord]],
    session: Session,
) -> tuple[list[MigrationOperation], dict[str, EntityCounts]]:
    """Compare planned records with read-only target state."""
    operations: list[MigrationOperation] = []
    counts = {entity: EntityCounts() for entity in planned.keys()}

    for entity_type, records in planned.items():
        entity_counts = counts[entity_type]
        entity_counts.source = snapshot.source_counts.get(
            {
                "companies": "companies_referenced",
                "vacancies": "vacancies_eligible",
                "applications": "applications",
                "people": "people",
                "daily_metrics": "daily_metrics",
                "hypotheses": "hypotheses",
                "assessments": "scoring_cat_a_eligible",
            }[entity_type],
            len(records),
        )
        entity_counts.eligible = len(records)
        for record in records:
            action_label, _existing = compare_with_target(
                session,
                entity_type,
                record.payload,
                source=record.identity.source,
                external_id=record.identity.external_id,
            )
            action = PlanAction(action_label)
            if action is PlanAction.PLANNED_INSERT:
                entity_counts.planned_insert += 1
            elif action is PlanAction.EXISTING_EQUIVALENT:
                entity_counts.existing_equivalent += 1
            elif action is PlanAction.CONFLICT:
                entity_counts.conflict += 1
            operations.append(
                MigrationOperation(
                    entity_type=entity_type,
                    action=action,
                    source_identity=record.identity,
                    parent_identity=record.parent,
                    reason=action.value.lower(),
                    warnings=list(record.warnings),
                )
            )

    deferred_ops = _deferred_operations(snapshot)
    operations.extend(deferred_ops)
    deferred_by_entity: dict[str, int] = {}
    for operation in deferred_ops:
        deferred_by_entity[operation.entity_type] = deferred_by_entity.get(operation.entity_type, 0) + 1
    for entity_type, deferred_count in deferred_by_entity.items():
        counts[entity_type].deferred += deferred_count

    return operations, counts
