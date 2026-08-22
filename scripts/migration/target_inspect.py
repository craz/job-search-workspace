"""Read-only inspection of the current Core PostgreSQL target."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from typing import Any

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from job_search_core.models import (
    Application,
    Assessment,
    Company,
    DailyMetric,
    Hypothesis,
    Person,
    Vacancy,
)

from scripts.migration.equivalence import records_equivalent


@contextmanager
def read_only_target_session(database_url: str) -> Iterator[Session]:
    """Open one read-only SQLAlchemy session and always roll back."""
    engine = create_engine(database_url, pool_pre_ping=True)
    if database_url.startswith("sqlite"):
        from job_search_core.models import Base

        Base.metadata.create_all(engine)
        session = Session(bind=engine, expire_on_commit=False)
        try:
            yield session
        finally:
            session.rollback()
            session.close()
            engine.dispose()
        return

    connection = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    connection.execute(text("BEGIN READ ONLY"))
    session = Session(bind=connection, expire_on_commit=False)
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        connection.close()
        engine.dispose()


def _company_payload(row: Company) -> dict[str, Any]:
    return {
        "name": row.name,
        "source": row.source,
        "external_id": row.external_id,
        "website_url": row.website_url,
    }


def _vacancy_payload(row: Vacancy) -> dict[str, Any]:
    return {
        "source": row.source,
        "external_id": row.external_id,
        "title": row.title,
        "url": row.url,
        "description": row.description,
        "status": row.status.value,
        "company_source": row.company.source,
        "company_external_id": row.company.external_id,
    }


def _application_payload(row: Application) -> dict[str, Any]:
    return {
        "source": row.source,
        "external_id": row.external_id,
        "applied_at": row.applied_at,
        "resume_version": row.resume_version,
        "cover_letter_version": row.cover_letter_version,
        "cover_letter_text": row.cover_letter_text,
        "result": row.result.value if row.result is not None else None,
        "next_action": row.next_action,
        "next_action_at": row.next_action_at,
        "vacancy_source": row.vacancy.source,
        "vacancy_external_id": row.vacancy.external_id,
    }


def _person_payload(row: Person) -> dict[str, Any]:
    return {
        "source": row.source,
        "external_id": row.external_id,
        "full_name": row.full_name,
        "role": row.role.value,
        "status": row.status.value,
        "title": row.title,
        "url": row.url,
        "confidence": row.confidence,
        "notes": row.notes,
        "company_source": row.company.source,
        "company_external_id": row.company.external_id,
        "vacancy_source": row.vacancy.source if row.vacancy is not None else None,
        "vacancy_external_id": row.vacancy.external_id if row.vacancy is not None else None,
    }


def _daily_metric_payload(row: DailyMetric) -> dict[str, Any]:
    return {
        "metric_date": row.metric_date.isoformat(),
        "views_total": row.views_total,
        "views_new": row.views_new,
        "applications": row.applications,
        "replies": row.replies,
        "invitations": row.invitations,
        "rejections": row.rejections,
        "notes": row.notes,
    }


def _hypothesis_payload(row: Hypothesis) -> dict[str, Any]:
    return {
        "source": row.source,
        "external_id": row.external_id,
        "title": row.title,
        "description": row.description,
        "test_size": row.test_size,
        "metric": row.metric,
        "status": row.status.value,
        "result": row.result,
    }


def _assessment_payload(row: Assessment) -> dict[str, Any]:
    return {
        "source": row.source,
        "external_id": row.external_id,
        "relevance_score": row.relevance_score,
        "verdict": row.verdict.value,
        "reason": row.reason,
        "risk": row.risk,
        "action": row.action,
        "model": row.model,
        "prompt_version": row.prompt_version,
        "assessed_at": row.assessed_at,
        "vacancy_source": row.vacancy.source,
        "vacancy_external_id": row.vacancy.external_id,
    }


def fetch_existing_payload(
    session: Session,
    entity_type: str,
    *,
    source: str | None,
    external_id: str,
) -> dict[str, Any] | None:
    """Load one normalized target payload by migration identity."""
    if entity_type == "companies":
        row = session.scalar(
            select(Company).where(Company.source == source, Company.external_id == external_id)
        )
        return _company_payload(row) if row else None
    if entity_type == "vacancies":
        row = session.scalar(
            select(Vacancy).where(Vacancy.source == source, Vacancy.external_id == external_id)
        )
        return _vacancy_payload(row) if row else None
    if entity_type == "applications":
        row = session.scalar(
            select(Application).where(
                Application.source == source,
                Application.external_id == external_id,
            )
        )
        return _application_payload(row) if row else None
    if entity_type == "people":
        row = session.scalar(
            select(Person).where(Person.source == source, Person.external_id == external_id)
        )
        return _person_payload(row) if row else None
    if entity_type == "daily_metrics":
        metric_date = date.fromisoformat(external_id)
        row = session.get(DailyMetric, metric_date)
        return _daily_metric_payload(row) if row else None
    if entity_type == "hypotheses":
        row = session.scalar(
            select(Hypothesis).where(Hypothesis.source == source, Hypothesis.external_id == external_id)
        )
        return _hypothesis_payload(row) if row else None
    if entity_type == "assessments":
        row = session.scalar(
            select(Assessment).where(
                Assessment.source == source,
                Assessment.external_id == external_id,
            )
        )
        return _assessment_payload(row) if row else None
    raise ValueError(f"unsupported entity type: {entity_type}")


def target_row_counts(session: Session) -> dict[str, int]:
    """Return current target table counts for zero-mutation verification."""
    return {
        "companies": session.scalar(select(func.count()).select_from(Company)),
        "vacancies": session.scalar(select(func.count()).select_from(Vacancy)),
        "applications": session.scalar(select(func.count()).select_from(Application)),
        "people": session.scalar(select(func.count()).select_from(Person)),
        "daily_metrics": session.scalar(select(func.count()).select_from(DailyMetric)),
        "hypotheses": session.scalar(select(func.count()).select_from(Hypothesis)),
        "assessments": session.scalar(select(func.count()).select_from(Assessment)),
    }


def compare_with_target(
    session: Session,
    entity_type: str,
    planned_payload: dict[str, Any],
    *,
    source: str | None,
    external_id: str,
) -> tuple[str, dict[str, Any] | None]:
    """Return action label and existing payload if present."""
    existing = fetch_existing_payload(
        session,
        entity_type,
        source=source,
        external_id=external_id,
    )
    if existing is None:
        return "PLANNED_INSERT", None
    if records_equivalent(entity_type, planned_payload, existing):
        return "EXISTING_EQUIVALENT", existing
    return "CONFLICT", existing
