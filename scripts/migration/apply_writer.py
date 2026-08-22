"""Write approved migration rows through Core application services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from job_search_core.applications import create_application
from job_search_core.assessments import create_assessment
from job_search_core.hypotheses import close_hypothesis, create_hypothesis
from job_search_core.metrics import set_daily_metric
from job_search_core.models import (
    ApplicationResult,
    AssessmentVerdict,
    Company,
    HypothesisStatus,
    PersonRole,
    PersonStatus,
    Vacancy,
    VacancyStatus,
)
from job_search_core.people import create_person, update_person_status
from job_search_core.schemas import (
    ApplicationCreate,
    AssessmentCreate,
    DailyMetricUpdate,
    HypothesisCreate,
    PersonCreate,
    VacancyCreate,
)
from job_search_core.vacancies import create_vacancy, request_fingerprint, update_vacancy_status

from scripts.migration.target_inspect import compare_with_target
from scripts.migration.types import PlannedRecord


class ApplyWriteError(RuntimeError):
    """Fatal migration write failure."""


@dataclass
class ApplyCounters:
    inserted: int = 0
    existing_equivalent: int = 0
    conflict: int = 0


def _parse_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def idempotency_key(run_id: str, record: PlannedRecord) -> str:
    source = record.identity.source or "none"
    return f"migrate-{run_id}-{record.entity_type}-{source}-{record.identity.external_id}"


def _resolve_company(session: Session, *, source: str, external_id: str) -> Company:
    company = session.scalar(
        select(Company).where(Company.source == source, Company.external_id == external_id)
    )
    if company is None:
        raise ApplyWriteError(f"missing company parent ({source}, {external_id})")
    return company


def _resolve_vacancy(session: Session, *, source: str, external_id: str) -> Vacancy:
    vacancy = session.scalar(
        select(Vacancy).where(Vacancy.source == source, Vacancy.external_id == external_id)
    )
    if vacancy is None:
        raise ApplyWriteError(f"missing vacancy parent ({source}, {external_id})")
    return vacancy


def apply_company(session: Session, record: PlannedRecord, *, run_id: str, counters: ApplyCounters) -> None:
    action, _existing = compare_with_target(
        session,
        "companies",
        record.payload,
        source=record.identity.source,
        external_id=record.identity.external_id,
    )
    if action == "EXISTING_EQUIVALENT":
        counters.existing_equivalent += 1
        return
    if action == "CONFLICT":
        counters.conflict += 1
        raise ApplyWriteError(f"company conflict for {record.identity.external_id}")

    company = Company(
        name=record.payload["name"],
        source=record.payload["source"],
        external_id=record.payload["external_id"],
        website_url=record.payload.get("website_url"),
    )
    session.add(company)
    session.flush()
    counters.inserted += 1


def _insert_vacancy_with_resolved_company(
    session: Session,
    record: PlannedRecord,
    *,
    run_id: str,
    company_name: str,
) -> Vacancy:
    """Insert one vacancy using the migrated company identity, not vacancy.source alone."""
    payload = record.payload
    company = _resolve_company(
        session,
        source=payload["company_source"],
        external_id=payload["company_external_id"],
    )
    request = VacancyCreate(
        company_name=company_name,
        company_external_id=payload["company_external_id"],
        source=payload["source"],
        external_id=payload["external_id"],
        title=payload["title"],
        url=payload["url"],
        description=payload.get("description"),
    )
    key = idempotency_key(run_id, record)
    existing = session.scalar(select(Vacancy).where(Vacancy.idempotency_key == key))
    if existing is not None:
        if existing.request_fingerprint != request_fingerprint(request):
            raise ApplyWriteError(f"vacancy idempotency conflict for {record.identity.external_id}")
        return existing

    duplicate = session.scalar(
        select(Vacancy).where(
            Vacancy.source == payload["source"],
            Vacancy.external_id == payload["external_id"],
        )
    )
    if duplicate is not None:
        raise ApplyWriteError(f"vacancy already exists for {record.identity.external_id}")

    vacancy = Vacancy(
        company=company,
        source=payload["source"],
        external_id=payload["external_id"],
        title=payload["title"],
        url=str(request.url),
        description=payload.get("description"),
        idempotency_key=key,
        request_fingerprint=request_fingerprint(request),
    )
    session.add(vacancy)
    session.flush()
    return vacancy


def apply_vacancy(
    session: Session,
    record: PlannedRecord,
    *,
    run_id: str,
    company_names: dict[tuple[str | None, str], str],
    counters: ApplyCounters,
) -> None:
    action, _existing = compare_with_target(
        session,
        "vacancies",
        record.payload,
        source=record.identity.source,
        external_id=record.identity.external_id,
    )
    if action == "EXISTING_EQUIVALENT":
        counters.existing_equivalent += 1
        return
    if action == "CONFLICT":
        counters.conflict += 1
        raise ApplyWriteError(f"vacancy conflict for {record.identity.external_id}")

    company_key = (record.payload["company_source"], record.payload["company_external_id"])
    company_name = company_names.get(company_key)
    if company_name is None:
        company_name = _resolve_company(
            session,
            source=record.payload["company_source"],
            external_id=record.payload["company_external_id"],
        ).name

    if record.payload["company_source"] == record.payload["source"]:
        request = VacancyCreate(
            company_name=company_name,
            company_external_id=record.payload["company_external_id"],
            source=record.payload["source"],
            external_id=record.payload["external_id"],
            title=record.payload["title"],
            url=record.payload["url"],
            description=record.payload.get("description"),
        )
        result = create_vacancy(session, request, idempotency_key(run_id, record))
        vacancy = result.vacancy
    else:
        vacancy = _insert_vacancy_with_resolved_company(
            session,
            record,
            run_id=run_id,
            company_name=company_name,
        )

    target_status = VacancyStatus(record.payload["status"])
    if vacancy.status != target_status:
        update_vacancy_status(session, vacancy.id, target_status)
    counters.inserted += 1


def apply_application(session: Session, record: PlannedRecord, *, run_id: str, counters: ApplyCounters) -> None:
    action, _existing = compare_with_target(
        session,
        "applications",
        record.payload,
        source=record.identity.source,
        external_id=record.identity.external_id,
    )
    if action == "EXISTING_EQUIVALENT":
        counters.existing_equivalent += 1
        return
    if action == "CONFLICT":
        counters.conflict += 1
        raise ApplyWriteError(f"application conflict for {record.identity.external_id}")

    assert record.parent is not None
    vacancy = _resolve_vacancy(
        session,
        source=record.parent.source,
        external_id=record.parent.external_id,
    )
    result_value = record.payload.get("result")
    request = ApplicationCreate(
        vacancy_id=vacancy.id,
        source=record.payload["source"],
        external_id=record.payload["external_id"],
        applied_at=_parse_datetime(record.payload["applied_at"]),
        resume_version=record.payload.get("resume_version"),
        cover_letter_version=record.payload.get("cover_letter_version"),
        cover_letter_text=record.payload.get("cover_letter_text"),
        result=ApplicationResult(result_value) if result_value is not None else None,
        next_action=record.payload.get("next_action"),
        next_action_at=(
            _parse_datetime(record.payload["next_action_at"])
            if record.payload.get("next_action_at")
            else None
        ),
    )
    create_application(session, request, idempotency_key(run_id, record))
    counters.inserted += 1


def apply_person(session: Session, record: PlannedRecord, *, run_id: str, counters: ApplyCounters) -> None:
    action, _existing = compare_with_target(
        session,
        "people",
        record.payload,
        source=record.identity.source,
        external_id=record.identity.external_id,
    )
    if action == "EXISTING_EQUIVALENT":
        counters.existing_equivalent += 1
        return
    if action == "CONFLICT":
        counters.conflict += 1
        raise ApplyWriteError(f"person conflict for {record.identity.external_id}")

    assert record.parent is not None
    company = _resolve_company(
        session,
        source=record.parent.source,
        external_id=record.parent.external_id,
    )
    vacancy_id = None
    vacancy_source = record.payload.get("vacancy_source")
    vacancy_external_id = record.payload.get("vacancy_external_id")
    if vacancy_source and vacancy_external_id:
        vacancy = _resolve_vacancy(session, source=vacancy_source, external_id=vacancy_external_id)
        vacancy_id = vacancy.id

    request = PersonCreate(
        company_id=company.id,
        vacancy_id=vacancy_id,
        source=record.payload["source"],
        external_id=record.payload["external_id"],
        full_name=record.payload["full_name"],
        role=PersonRole(record.payload["role"]),
        title=record.payload.get("title"),
        url=record.payload.get("url"),
        confidence=record.payload.get("confidence"),
        notes=record.payload.get("notes"),
    )
    result = create_person(session, request, idempotency_key(run_id, record))
    target_status = PersonStatus(record.payload["status"])
    if result.person.status != target_status:
        update_person_status(session, result.person.id, target_status)
    counters.inserted += 1


def apply_assessment(session: Session, record: PlannedRecord, *, run_id: str, counters: ApplyCounters) -> None:
    action, _existing = compare_with_target(
        session,
        "assessments",
        record.payload,
        source=record.identity.source,
        external_id=record.identity.external_id,
    )
    if action == "EXISTING_EQUIVALENT":
        counters.existing_equivalent += 1
        return
    if action == "CONFLICT":
        counters.conflict += 1
        raise ApplyWriteError(f"assessment conflict for {record.identity.external_id}")

    assert record.parent is not None
    vacancy = _resolve_vacancy(
        session,
        source=record.parent.source,
        external_id=record.parent.external_id,
    )
    request = AssessmentCreate(
        vacancy_id=vacancy.id,
        source=record.payload["source"],
        external_id=record.payload["external_id"],
        relevance_score=record.payload["relevance_score"],
        verdict=AssessmentVerdict(record.payload["verdict"]),
        reason=record.payload["reason"],
        risk=record.payload.get("risk"),
        action=record.payload["action"],
        model=record.payload["model"],
        prompt_version=record.payload["prompt_version"],
        assessed_at=_parse_datetime(record.payload["assessed_at"]),
    )
    create_assessment(session, request, idempotency_key(run_id, record))
    counters.inserted += 1


def apply_daily_metric(session: Session, record: PlannedRecord, *, run_id: str, counters: ApplyCounters) -> None:
    action, _existing = compare_with_target(
        session,
        "daily_metrics",
        record.payload,
        source=record.identity.source,
        external_id=record.identity.external_id,
    )
    if action == "EXISTING_EQUIVALENT":
        counters.existing_equivalent += 1
        return
    if action == "CONFLICT":
        counters.conflict += 1
        raise ApplyWriteError(f"daily metric conflict for {record.identity.external_id}")

    metric_date = date.fromisoformat(record.payload["metric_date"])
    request = DailyMetricUpdate(
        views_total=record.payload.get("views_total"),
        views_new=record.payload.get("views_new"),
        applications=record.payload.get("applications"),
        replies=record.payload.get("replies"),
        invitations=record.payload.get("invitations"),
        rejections=record.payload.get("rejections"),
        notes=record.payload.get("notes"),
    )
    set_daily_metric(session, metric_date, request, idempotency_key(run_id, record))
    counters.inserted += 1


def apply_hypothesis(session: Session, record: PlannedRecord, *, run_id: str, counters: ApplyCounters) -> None:
    action, _existing = compare_with_target(
        session,
        "hypotheses",
        record.payload,
        source=record.identity.source,
        external_id=record.identity.external_id,
    )
    if action == "EXISTING_EQUIVALENT":
        counters.existing_equivalent += 1
        return
    if action == "CONFLICT":
        counters.conflict += 1
        raise ApplyWriteError(f"hypothesis conflict for {record.identity.external_id}")

    request = HypothesisCreate(
        source=record.payload["source"],
        external_id=record.payload["external_id"],
        title=record.payload["title"],
        description=record.payload.get("description"),
        test_size=record.payload.get("test_size"),
        metric=record.payload.get("metric"),
    )
    result = create_hypothesis(session, request, idempotency_key(run_id, record))
    if record.payload["status"] == HypothesisStatus.DONE.value:
        close_hypothesis(session, result.hypothesis.id, record.payload.get("result") or "")
    counters.inserted += 1


def apply_planned_records(
    session: Session,
    planned: dict[str, list[PlannedRecord]],
    *,
    run_id: str,
) -> dict[str, ApplyCounters]:
    """Apply the approved first slice in FK-safe order inside one transaction."""
    company_names = {
        (item.identity.source, item.identity.external_id): item.payload["name"]
        for item in planned["companies"]
    }
    counters = {entity: ApplyCounters() for entity in planned.keys()}

    for record in planned["companies"]:
        apply_company(session, record, run_id=run_id, counters=counters["companies"])
    for record in planned["vacancies"]:
        apply_vacancy(
            session,
            record,
            run_id=run_id,
            company_names=company_names,
            counters=counters["vacancies"],
        )
    for record in planned["applications"]:
        apply_application(session, record, run_id=run_id, counters=counters["applications"])
    for record in planned["people"]:
        apply_person(session, record, run_id=run_id, counters=counters["people"])
    for record in planned["assessments"]:
        apply_assessment(session, record, run_id=run_id, counters=counters["assessments"])
    for record in planned["daily_metrics"]:
        apply_daily_metric(session, record, run_id=run_id, counters=counters["daily_metrics"])
    for record in planned["hypotheses"]:
        apply_hypothesis(session, record, run_id=run_id, counters=counters["hypotheses"])

    return counters
