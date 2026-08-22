"""Honest vacancy URL resolution for legacy migration."""

from __future__ import annotations

from typing import Any

from scripts.migration.constants import HH_VACANCY_URL_TEMPLATE
from scripts.migration.source_reader import extract_hh_vacancy_id


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def resolve_vacancy_hh_id(row: dict[str, Any], *, people_hh_vacancy_id: str | None = None) -> str | None:
    """Return a trusted HH vacancy id from legacy vacancy URL or linked Person field."""
    return extract_hh_vacancy_id(row.get("url")) or _blank_to_none(people_hh_vacancy_id)


def resolve_vacancy_url(
    row: dict[str, Any],
    *,
    people_hh_vacancy_id: str | None = None,
) -> tuple[str | None, list[str]]:
    """Resolve vacancy URL from source only — never substitute Company URL or placeholders."""
    direct = _blank_to_none(row.get("url"))
    if direct:
        return direct, []
    hh_id = resolve_vacancy_hh_id(row, people_hh_vacancy_id=people_hh_vacancy_id)
    if hh_id:
        return HH_VACANCY_URL_TEMPLATE.format(vacancy_id=hh_id), ["reconstructed_from_hh_vacancy_id"]
    return None, []
