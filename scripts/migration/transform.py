"""Map legacy rows into normalized migration payloads."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from scripts.migration.constants import (
    APPLICATION_RESULT_MAP,
    ASSESSMENT_ACTION_MAP,
    PERSON_SOURCE_NORMALIZE,
    PROMPT_VERSION_SENTINEL,
    SOURCE_HH,
    SOURCE_LEGACY,
    SOURCE_SCORING,
    VACANCY_STATUS_MAP,
)
from scripts.migration.source_reader import extract_hh_vacancy_id
from scripts.migration.vacancy_url import resolve_vacancy_hh_id, resolve_vacancy_url
from scripts.migration.types import LegacyAnomaly, LegacySnapshot, ParentIdentity, PlannedRecord, SourceIdentity


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def vacancy_identity(row: dict[str, Any], *, people_hh_vacancy_id: str | None = None) -> SourceIdentity:
    hh_id = resolve_vacancy_hh_id(row, people_hh_vacancy_id=people_hh_vacancy_id)
    if hh_id:
        return SourceIdentity(
            entity_type="vacancies",
            source=SOURCE_HH,
            external_id=hh_id,
            legacy_key=f"vacancy:{row['id']}",
        )
    return SourceIdentity(
        entity_type="vacancies",
        source=SOURCE_LEGACY,
        external_id=f"vacancy-{row['id']}",
        legacy_key=f"vacancy:{row['id']}",
    )


def transform_vacancies(snapshot: LegacySnapshot) -> list[PlannedRecord]:
    company_by_id = {row["id"]: row for row in snapshot.companies}
    records: list[PlannedRecord] = []
    for row in snapshot.vacancies:
        company_row = company_by_id[row["company_id"]]
        parent = company_identity(company_row)
        people_hh = snapshot.people_hh_by_vacancy_id.get(int(row["id"]))
        identity = vacancy_identity(row, people_hh_vacancy_id=people_hh)
        status = row.get("status") or "found"
        if status not in VACANCY_STATUS_MAP:
            raise ValueError(f"unknown vacancy status: {status}")
        url, url_warnings = resolve_vacancy_url(row, people_hh_vacancy_id=people_hh)
        if url is None:
            raise ValueError(f"vacancy {row['id']} reached transform without reconstructable URL")
        records.append(
            PlannedRecord(
                entity_type="vacancies",
                identity=identity,
                parent=ParentIdentity("companies", parent.source or SOURCE_LEGACY, parent.external_id),
                payload={
                    "source": identity.source,
                    "external_id": identity.external_id,
                    "title": row["title"],
                    "url": url,
                    "description": None,
                    "status": VACANCY_STATUS_MAP[status],
                    "company_source": parent.source,
                    "company_external_id": parent.external_id,
                },
                warnings=url_warnings,
            )
        )
    return records


def company_identity(row: dict[str, Any]) -> SourceIdentity:
    employer_id = _blank_to_none(row.get("employer_id"))
    if employer_id:
        return SourceIdentity(
            entity_type="companies",
            source=SOURCE_HH,
            external_id=employer_id,
            legacy_key=f"company:{row['id']}",
        )
    return SourceIdentity(
        entity_type="companies",
        source=SOURCE_LEGACY,
        external_id=f"company-{row['id']}",
        legacy_key=f"company:{row['id']}",
    )


def transform_companies(snapshot: LegacySnapshot) -> list[PlannedRecord]:
    records: list[PlannedRecord] = []
    for row in snapshot.companies:
        identity = company_identity(row)
        records.append(
            PlannedRecord(
                entity_type="companies",
                identity=identity,
                payload={
                    "name": row["name"],
                    "source": identity.source,
                    "external_id": identity.external_id,
                    "website_url": _blank_to_none(row.get("site_url")),
                },
            )
        )
    return records


def transform_applications(
    snapshot: LegacySnapshot,
    *,
    anomalies: list[LegacyAnomaly],
) -> list[PlannedRecord]:
    vacancy_by_id = {row["id"]: row for row in snapshot.vacancies}
    records: list[PlannedRecord] = []
    for row in snapshot.applications:
        vacancy_row = vacancy_by_id[row["vacancy_id"]]
        people_hh = snapshot.people_hh_by_vacancy_id.get(int(vacancy_row["id"]))
        parent = vacancy_identity(vacancy_row, people_hh_vacancy_id=people_hh)
        identity = SourceIdentity(
            entity_type="applications",
            source=SOURCE_LEGACY,
            external_id=f"application-{row['id']}",
            legacy_key=f"application:{row['id']}",
        )
        legacy_result = row.get("result")
        target_result: str | None
        warnings: list[str] = []
        if legacy_result is None:
            target_result = None
        elif legacy_result == "автоответ":
            target_result = None
            anomalies.append(
                LegacyAnomaly(
                    code="legacy_result_autoreply",
                    entity_type="applications",
                    legacy_key=identity.legacy_key or identity.external_id,
                    message='Legacy result "автоответ" imported as NULL Application.result',
                )
            )
        elif legacy_result in APPLICATION_RESULT_MAP:
            target_result = APPLICATION_RESULT_MAP[legacy_result]
        else:
            raise ValueError(f"unknown application result: {legacy_result!r}")

        applied_at = _parse_datetime(row.get("applied_at"))
        if applied_at is None:
            raise ValueError(f"application {row['id']} missing applied_at")

        records.append(
            PlannedRecord(
                entity_type="applications",
                identity=identity,
                parent=ParentIdentity("vacancies", parent.source or SOURCE_LEGACY, parent.external_id),
                payload={
                    "source": SOURCE_LEGACY,
                    "external_id": identity.external_id,
                    "applied_at": applied_at.isoformat(),
                    "resume_version": _blank_to_none(row.get("resume_version")),
                    "cover_letter_version": _blank_to_none(row.get("cover_letter_version")),
                    "cover_letter_text": row.get("cover_letter_text"),
                    "result": target_result,
                    "next_action": _blank_to_none(row.get("next_action")),
                    "next_action_at": (
                        _parse_datetime(row.get("next_action_date")).isoformat()
                        if _parse_datetime(row.get("next_action_date"))
                        else None
                    ),
                },
                warnings=warnings,
            )
        )
    return records


def transform_people(snapshot: LegacySnapshot) -> list[PlannedRecord]:
    company_by_id = {row["id"]: row for row in snapshot.companies}
    vacancy_by_id = {row["id"]: row for row in snapshot.vacancies}
    records: list[PlannedRecord] = []
    for row in snapshot.people:
        company_row = company_by_id[row["company_id"]]
        company = company_identity(company_row)
        identity = SourceIdentity(
            entity_type="people",
            source=SOURCE_LEGACY,
            external_id=f"person-{row['id']}",
            legacy_key=f"person:{row['id']}",
        )
        raw_source = _blank_to_none(row.get("source")) or SOURCE_LEGACY
        normalized_source = PERSON_SOURCE_NORMALIZE.get(raw_source, raw_source)
        parent = ParentIdentity("companies", company.source or SOURCE_LEGACY, company.external_id)
        vacancy_parent = None
        if row.get("vacancy_id") is not None:
            vacancy_row = vacancy_by_id.get(row["vacancy_id"])
            if vacancy_row is not None:
                people_hh = snapshot.people_hh_by_vacancy_id.get(int(vacancy_row["id"]))
                vac = vacancy_identity(vacancy_row, people_hh_vacancy_id=people_hh)
                vacancy_parent = ParentIdentity("vacancies", vac.source or SOURCE_LEGACY, vac.external_id)
        records.append(
            PlannedRecord(
                entity_type="people",
                identity=identity,
                parent=parent,
                payload={
                    "source": normalized_source,
                    "external_id": identity.external_id,
                    "full_name": row["full_name"],
                    "role": row["role"],
                    "status": row["status"],
                    "title": _blank_to_none(row.get("title")),
                    "url": _blank_to_none(row.get("url")),
                    "confidence": row.get("confidence"),
                    "notes": _blank_to_none(row.get("notes")),
                    "company_source": parent.source,
                    "company_external_id": parent.external_id,
                    "vacancy_source": vacancy_parent.source if vacancy_parent else None,
                    "vacancy_external_id": vacancy_parent.external_id if vacancy_parent else None,
                },
            )
        )
    return records


def transform_daily_metrics(snapshot: LegacySnapshot) -> list[PlannedRecord]:
    records: list[PlannedRecord] = []
    for row in snapshot.daily_metrics:
        metric_date = _parse_date(row["date"])
        identity = SourceIdentity(
            entity_type="daily_metrics",
            source=None,
            external_id=metric_date.isoformat(),
            legacy_key=f"metric:{metric_date.isoformat()}",
        )
        records.append(
            PlannedRecord(
                entity_type="daily_metrics",
                identity=identity,
                payload={
                    "metric_date": metric_date.isoformat(),
                    "views_total": row.get("views_total"),
                    "views_new": row.get("views_new"),
                    "applications": row.get("applications"),
                    "replies": row.get("replies"),
                    "invitations": row.get("invitations"),
                    "rejections": row.get("rejections"),
                    "notes": _blank_to_none(row.get("notes")),
                },
            )
        )
    return records


def transform_hypotheses(snapshot: LegacySnapshot) -> list[PlannedRecord]:
    records: list[PlannedRecord] = []
    for row in snapshot.hypotheses:
        status = row.get("status") or "active"
        if status not in {"active", "done"}:
            raise ValueError(f"unknown hypothesis status: {status}")
        identity = SourceIdentity(
            entity_type="hypotheses",
            source=SOURCE_LEGACY,
            external_id=f"hypothesis-{row['id']}",
            legacy_key=f"hypothesis:{row['id']}",
        )
        records.append(
            PlannedRecord(
                entity_type="hypotheses",
                identity=identity,
                payload={
                    "source": SOURCE_LEGACY,
                    "external_id": identity.external_id,
                    "title": row["title"],
                    "description": _blank_to_none(row.get("description")),
                    "test_size": row.get("test_size"),
                    "metric": _blank_to_none(row.get("metric")),
                    "status": status,
                    "result": _blank_to_none(row.get("result")),
                },
            )
        )
    return records


def _join_reason(score: dict[str, Any]) -> str:
    reasons = score.get("reasons") or []
    if not reasons:
        raise ValueError("assessment missing reasons")
    return "\n".join(str(item).strip() for item in reasons if str(item).strip())


def _join_risk(score: dict[str, Any]) -> str | None:
    parts: list[str] = []
    for key in ("mismatches", "strengths"):
        values = score.get(key) or []
        for item in values:
            text = str(item).strip()
            if text:
                parts.append(text)
    return "\n".join(parts) if parts else None


def transform_assessments(snapshot: LegacySnapshot) -> list[PlannedRecord]:
    vacancy_by_hh: dict[str, dict[str, Any]] = {}
    for row in snapshot.vacancies:
        hh_id = extract_hh_vacancy_id(row.get("url"))
        if hh_id:
            vacancy_by_hh[hh_id] = row

    records: list[PlannedRecord] = []
    for record in snapshot.scoring_rows:
        score = record.get("score") or {}
        hh_id = str(score.get("vacancy_id") or (record.get("vacancy") or {}).get("vacancy_id"))
        vacancy_row = vacancy_by_hh.get(hh_id)
        if vacancy_row is None:
            continue
        parent = vacancy_identity(vacancy_row, people_hh_vacancy_id=snapshot.people_hh_by_vacancy_id.get(int(vacancy_row["id"])))
        verdict = score.get("verdict")
        if verdict not in ASSESSMENT_ACTION_MAP:
            raise ValueError(f"unknown assessment verdict: {verdict!r}")
        relevance = score.get("score")
        if relevance is None or not (0 <= int(relevance) <= 100):
            raise ValueError(f"invalid assessment score for hh {hh_id}")
        assessed_at = _parse_datetime(score.get("scored_at"))
        if assessed_at is None:
            raise ValueError(f"assessment for hh {hh_id} missing scored_at")
        method = score.get("method") or "unknown"
        identity = SourceIdentity(
            entity_type="assessments",
            source=SOURCE_SCORING,
            external_id=hh_id,
            legacy_key=f"assessment:hh:{hh_id}",
        )
        records.append(
            PlannedRecord(
                entity_type="assessments",
                identity=identity,
                parent=ParentIdentity("vacancies", parent.source or SOURCE_HH, parent.external_id),
                payload={
                    "source": SOURCE_SCORING,
                    "external_id": hh_id,
                    "relevance_score": int(relevance),
                    "verdict": verdict,
                    "reason": _join_reason(score),
                    "risk": _join_risk(score),
                    "action": ASSESSMENT_ACTION_MAP[verdict],
                    "model": f"legacy:{method}",
                    "prompt_version": PROMPT_VERSION_SENTINEL,
                    "assessed_at": assessed_at.isoformat(),
                    "vacancy_source": parent.source,
                    "vacancy_external_id": parent.external_id,
                },
            )
        )
    return records


def transform_snapshot(
    snapshot: LegacySnapshot,
    *,
    anomalies: list[LegacyAnomaly],
) -> dict[str, list[PlannedRecord]]:
    """Transform all approved legacy datasets into planned records."""
    return {
        "companies": transform_companies(snapshot),
        "vacancies": transform_vacancies(snapshot),
        "applications": transform_applications(snapshot, anomalies=anomalies),
        "people": transform_people(snapshot),
        "daily_metrics": transform_daily_metrics(snapshot),
        "hypotheses": transform_hypotheses(snapshot),
        "assessments": transform_assessments(snapshot),
    }
