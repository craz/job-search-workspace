"""Honest vacancy URL resolution for legacy migration."""

from __future__ import annotations

import re
from typing import Any

from scripts.migration.constants import HH_VACANCY_URL_TEMPLATE
from scripts.migration.source_reader import extract_hh_vacancy_id


_PLACEHOLDER_DOMAIN = "legacy.job-search.invalid"
_HH_EMPLOYER_URL_RE = re.compile(r"^https?://[^/]*hh\.ru/employer/\d+/?$", re.IGNORECASE)


def _normalize_url(url: str) -> str:
    """Normalize scheme/host and strip trailing slash for safe equality checks."""
    value = url.strip()
    # scheme://host/path  (we intentionally do not parse query/fragment for migration policy)
    scheme, rest = value.split("://", 1) if "://" in value else ("", value)
    scheme = scheme.lower()
    if scheme:
        host_path = rest
    else:
        host_path = rest
    if "/" in host_path:
        host, path = host_path.split("/", 1)
        path = "/" + path
    else:
        host, path = host_path, ""
    host = host.lower()
    path = path.rstrip("/")
    return f"{scheme + '://' if scheme else ''}{host}{path}"


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
    company_hh_url: str | None = None,
) -> tuple[str | None, list[str]]:
    """Resolve vacancy URL from source only — never substitute Company URL or placeholders."""
    direct = _blank_to_none(row.get("url"))

    if direct:
        norm_direct = _normalize_url(direct)

        # Never accept the legacy synthetic placeholder domain as a vacancy URL.
        if _PLACEHOLDER_DOMAIN in norm_direct:
            return None, ["placeholder_domain_rejected"]

        # Reject employer/company profile pages (contract requires vacancy/listing URL semantics).
        if _HH_EMPLOYER_URL_RE.match(norm_direct):
            return None, ["employer_page_rejected"]

        # Reject direct URL that is semantically equal to company hh_url.
        if company_hh_url:
            norm_company = _normalize_url(company_hh_url)
            if norm_company == norm_direct:
                return None, ["vacancy_url_equals_company_hh_url"]

        return direct, []

    hh_id = resolve_vacancy_hh_id(row, people_hh_vacancy_id=people_hh_vacancy_id)
    if hh_id:
        return HH_VACANCY_URL_TEMPLATE.format(vacancy_id=hh_id), ["reconstructed_from_hh_vacancy_id"]
    return None, []
