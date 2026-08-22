"""Semantic equivalence checks between planned payloads and target rows."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any


def _parse_iso_datetime(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def equivalent_company(planned: dict[str, Any], existing: dict[str, Any]) -> bool:
    return (
        planned["name"] == existing["name"]
        and planned["source"] == existing["source"]
        and planned["external_id"] == existing["external_id"]
        and _normalize_optional_text(planned.get("website_url"))
        == _normalize_optional_text(existing.get("website_url"))
    )


def equivalent_vacancy(planned: dict[str, Any], existing: dict[str, Any]) -> bool:
    return (
        planned["source"] == existing["source"]
        and planned["external_id"] == existing["external_id"]
        and planned["title"] == existing["title"]
        and planned["url"] == existing["url"]
        and _normalize_optional_text(planned.get("description"))
        == _normalize_optional_text(existing.get("description"))
        and planned["status"] == existing["status"]
        and planned["company_source"] == existing["company_source"]
        and planned["company_external_id"] == existing["company_external_id"]
    )


def equivalent_application(planned: dict[str, Any], existing: dict[str, Any]) -> bool:
    return (
        planned["source"] == existing["source"]
        and planned["external_id"] == existing["external_id"]
        and _parse_iso_datetime(planned["applied_at"]) == _parse_iso_datetime(existing["applied_at"])
        and planned.get("resume_version") == existing.get("resume_version")
        and planned.get("cover_letter_version") == existing.get("cover_letter_version")
        and planned.get("cover_letter_text") == existing.get("cover_letter_text")
        and planned.get("result") == existing.get("result")
        and _normalize_optional_text(planned.get("next_action"))
        == _normalize_optional_text(existing.get("next_action"))
        and _parse_iso_datetime(planned.get("next_action_at"))
        == _parse_iso_datetime(existing.get("next_action_at"))
        and planned["vacancy_source"] == existing["vacancy_source"]
        and planned["vacancy_external_id"] == existing["vacancy_external_id"]
    )


def equivalent_person(planned: dict[str, Any], existing: dict[str, Any]) -> bool:
    return (
        planned["source"] == existing["source"]
        and planned["external_id"] == existing["external_id"]
        and planned["full_name"] == existing["full_name"]
        and planned["role"] == existing["role"]
        and planned["status"] == existing["status"]
        and _normalize_optional_text(planned.get("title")) == _normalize_optional_text(existing.get("title"))
        and _normalize_optional_text(planned.get("url")) == _normalize_optional_text(existing.get("url"))
        and planned.get("confidence") == existing.get("confidence")
        and _normalize_optional_text(planned.get("notes")) == _normalize_optional_text(existing.get("notes"))
        and planned["company_source"] == existing["company_source"]
        and planned["company_external_id"] == existing["company_external_id"]
        and planned.get("vacancy_source") == existing.get("vacancy_source")
        and planned.get("vacancy_external_id") == existing.get("vacancy_external_id")
    )


def equivalent_daily_metric(planned: dict[str, Any], existing: dict[str, Any]) -> bool:
    return all(
        planned.get(field) == existing.get(field)
        for field in (
            "metric_date",
            "views_total",
            "views_new",
            "applications",
            "replies",
            "invitations",
            "rejections",
            "notes",
        )
    )


def equivalent_hypothesis(planned: dict[str, Any], existing: dict[str, Any]) -> bool:
    return (
        planned["source"] == existing["source"]
        and planned["external_id"] == existing["external_id"]
        and planned["title"] == existing["title"]
        and _normalize_optional_text(planned.get("description"))
        == _normalize_optional_text(existing.get("description"))
        and planned.get("test_size") == existing.get("test_size")
        and _normalize_optional_text(planned.get("metric")) == _normalize_optional_text(existing.get("metric"))
        and planned["status"] == existing["status"]
        and _normalize_optional_text(planned.get("result")) == _normalize_optional_text(existing.get("result"))
    )


def equivalent_assessment(planned: dict[str, Any], existing: dict[str, Any]) -> bool:
    return (
        planned["source"] == existing["source"]
        and planned["external_id"] == existing["external_id"]
        and planned["relevance_score"] == existing["relevance_score"]
        and planned["verdict"] == existing["verdict"]
        and planned["reason"] == existing["reason"]
        and _normalize_optional_text(planned.get("risk")) == _normalize_optional_text(existing.get("risk"))
        and planned["action"] == existing["action"]
        and planned["model"] == existing["model"]
        and planned["prompt_version"] == existing["prompt_version"]
        and _parse_iso_datetime(planned["assessed_at"]) == _parse_iso_datetime(existing["assessed_at"])
        and planned["vacancy_source"] == existing["vacancy_source"]
        and planned["vacancy_external_id"] == existing["vacancy_external_id"]
    )


def records_equivalent(entity_type: str, planned: dict[str, Any], existing: dict[str, Any]) -> bool:
    """Compare migration-owned semantic fields for one entity type."""
    if entity_type == "companies":
        return equivalent_company(planned, existing)
    if entity_type == "vacancies":
        return equivalent_vacancy(planned, existing)
    if entity_type == "applications":
        return equivalent_application(planned, existing)
    if entity_type == "people":
        return equivalent_person(planned, existing)
    if entity_type == "daily_metrics":
        return equivalent_daily_metric(planned, existing)
    if entity_type == "hypotheses":
        return equivalent_hypothesis(planned, existing)
    if entity_type == "assessments":
        return equivalent_assessment(planned, existing)
    raise ValueError(f"unsupported entity type: {entity_type}")
