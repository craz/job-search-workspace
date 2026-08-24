"""Read-only legacy SQLite and JSONL loaders for the first migration slice."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from scripts.migration.constants import EXPECTED_DEFERRED_COUNTS, HH_VACANCY_URL_TEMPLATE
from scripts.migration.types import LegacySnapshot

HH_VACANCY_ID = re.compile(r"/vacancy/(\d+)")


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    """Open legacy SQLite strictly read-only."""
    uri = f"file:{db_path}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def extract_hh_vacancy_id(url: str | None) -> str | None:
    """Extract HH vacancy id from a legacy vacancy URL."""
    if not url:
        return None
    match = HH_VACANCY_ID.search(url)
    return match.group(1) if match else None


def vacancy_has_importable_url(row: dict[str, Any], *, people_hh_vacancy_id: str | None = None) -> bool:
    """Return True when a real or reconstructable vacancy URL exists in source.

    Policy:
    - vacancy URL is valid only if it is a vacancy/listing URL (not employer/company profile pages),
      and not the legacy synthetic placeholder domain.
    - If a trusted HH vacancy id exists in `people.hh_vacancy_id`, we accept reconstruction.
    """
    return vacancy_has_importable_url_strict(
        row,
        people_hh_vacancy_id=people_hh_vacancy_id,
        company_hh_url=None,
    )


def _normalize_url(url: str) -> str:
    value = url.strip()
    scheme, rest = value.split("://", 1) if "://" in value else ("", value)
    scheme = scheme.lower()
    host_path = rest
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


_PLACEHOLDER_DOMAIN = "legacy.job-search.invalid"
_HH_EMPLOYER_URL_RE = re.compile(r"^https?://[^/]*hh\.ru/employer/\d+/?$", re.IGNORECASE)


def vacancy_has_importable_url_strict(
    row: dict[str, Any],
    *,
    people_hh_vacancy_id: str | None = None,
    company_hh_url: str | None = None,
) -> bool:
    """Strict vacancy URL importability check (used by DATA-00.6 remediation)."""
    trusted_hh_id = _blank_to_none(people_hh_vacancy_id)
    if trusted_hh_id:
        return True

    direct = _blank_to_none(row.get("url"))
    if not direct:
        return False

    norm_direct = _normalize_url(direct)

    if _PLACEHOLDER_DOMAIN in norm_direct:
        return False

    if _HH_EMPLOYER_URL_RE.match(norm_direct):
        return False

    if company_hh_url:
        norm_company = _normalize_url(company_hh_url)
        if norm_company == norm_direct:
            return False

    return True


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _row_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def _load_sqlite_tables(connection: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    tables = {}
    for name in ("companies", "vacancies", "applications", "people", "daily_metrics", "hypotheses"):
        rows = connection.execute(f"SELECT * FROM {name}").fetchall()
        tables[name] = [_row_dict(row) for row in rows]
    return tables


def _score_vacancy_id(record: dict[str, Any]) -> str | None:
    score = record.get("score") or {}
    vacancy = record.get("vacancy") or {}
    raw = score.get("vacancy_id") or vacancy.get("vacancy_id")
    return str(raw) if raw is not None else None


def _score_scored_at(record: dict[str, Any]) -> str | None:
    score = record.get("score") or {}
    return score.get("scored_at")


def load_legacy_snapshot(legacy_root: Path) -> LegacySnapshot:
    """Load approved and deferred legacy datasets without mutating source."""
    db_path = legacy_root / "data/job_search.db"
    jsonl_path = legacy_root / "data/vacancy_scores.jsonl"

    with _connect_readonly(db_path) as connection:
        tables = _load_sqlite_tables(connection)

    company_by_id = {row["id"]: row for row in tables["companies"]}

    referenced_company_ids = {
        row["company_id"]
        for row in tables["vacancies"]
        if row.get("company_id") is not None
    } | {row["company_id"] for row in tables["people"]}

    companies = [row for row in tables["companies"] if row["id"] in referenced_company_ids]
    watch_only = [row for row in tables["companies"] if row["id"] not in referenced_company_ids]

    people_hh_by_vacancy_id: dict[int, str] = {}
    for person in tables["people"]:
        hh_id = _blank_to_none(person.get("hh_vacancy_id"))
        if hh_id and person.get("vacancy_id") is not None:
            people_hh_by_vacancy_id[int(person["vacancy_id"])] = hh_id

    with_company = [row for row in tables["vacancies"] if row.get("company_id") is not None]
    vacancies = [
        row
        for row in with_company
        if vacancy_has_importable_url_strict(
            row,
            people_hh_vacancy_id=people_hh_by_vacancy_id.get(int(row["id"])),
            company_hh_url=_blank_to_none(company_by_id[int(row["company_id"])].get("hh_url")),
        )
    ]
    vacancies_missing_url = [
        row
        for row in with_company
        if not vacancy_has_importable_url_strict(
            row,
            people_hh_vacancy_id=people_hh_by_vacancy_id.get(int(row["id"])),
            company_hh_url=_blank_to_none(company_by_id[int(row["company_id"])].get("hh_url")),
        )
    ]
    orphan_vacancies = [row for row in tables["vacancies"] if row.get("company_id") is None]

    hh_vacancy_ids = {
        hh_id
        for row in tables["vacancies"]
        if (hh_id := extract_hh_vacancy_id(row.get("url")))
    }
    eligible_hh_vacancy_ids = {
        hh_id
        for row in vacancies
        if (hh_id := extract_hh_vacancy_id(row.get("url")))
    }

    embedded_assessment_vacancy_ids = [
        row["id"]
        for row in tables["vacancies"]
        if any(row.get(field) for field in ("reason", "risk", "action"))
    ]

    scoring_rows: list[dict[str, Any]] = []
    scoring_deferred_off_db: list[dict[str, Any]] = []
    scoring_deferred_history: list[dict[str, Any]] = []
    scoring_deferred_orphan: list[dict[str, Any]] = []
    latest_by_hh: dict[str, dict[str, Any]] = {}

    for line_number, line in enumerate(jsonl_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        record = json.loads(line)
        record["_line_number"] = line_number
        hh_id = _score_vacancy_id(record)
        if hh_id is None:
            continue
        if hh_id in hh_vacancy_ids:
            previous = latest_by_hh.get(hh_id)
            if previous is not None:
                scoring_deferred_history.append(previous)
            latest_by_hh[hh_id] = record
        else:
            scoring_deferred_off_db.append(record)

    eligible_latest: dict[str, dict[str, Any]] = {}
    orphan_latest: dict[str, dict[str, Any]] = {}
    for hh_id, record in latest_by_hh.items():
        if hh_id in eligible_hh_vacancy_ids:
            eligible_latest[hh_id] = record
        elif hh_id in {extract_hh_vacancy_id(row.get("url")) for row in orphan_vacancies}:
            orphan_latest[hh_id] = record

    scoring_rows = list(eligible_latest.values())
    scoring_deferred_orphan = list(orphan_latest.values())

    source_counts = {
        "companies_total": len(tables["companies"]),
        "companies_referenced": len(companies),
        "vacancies_with_company": len(with_company),
        "vacancies_eligible": len(vacancies),
        "vacancies_missing_url": len(vacancies_missing_url),
        "vacancies_without_company": len(orphan_vacancies),
        "applications": len(tables["applications"]),
        "people": len(tables["people"]),
        "daily_metrics": len(tables["daily_metrics"]),
        "hypotheses": len(tables["hypotheses"]),
        "scoring_jsonl_lines": sum(1 for _ in jsonl_path.read_text(encoding="utf-8").splitlines() if _.strip()),
        "scoring_cat_a_unique": len(latest_by_hh),
        "scoring_cat_a_eligible": len(scoring_rows),
        "scoring_cat_a_orphan_linked": len(scoring_deferred_orphan),
    }

    deferred_counts = {
        **EXPECTED_DEFERRED_COUNTS,
        "historical_score_lines": len(scoring_deferred_history),
        "off_db_score_lines": len(scoring_deferred_off_db),
    }

    return LegacySnapshot(
        companies=companies,
        watch_only_companies=watch_only,
        vacancies=vacancies,
        vacancies_missing_url=vacancies_missing_url,
        orphan_vacancies=orphan_vacancies,
        people_hh_by_vacancy_id=people_hh_by_vacancy_id,
        applications=tables["applications"],
        people=tables["people"],
        daily_metrics=tables["daily_metrics"],
        hypotheses=tables["hypotheses"],
        scoring_rows=scoring_rows,
        scoring_deferred_off_db=scoring_deferred_off_db,
        scoring_deferred_history=scoring_deferred_history,
        scoring_deferred_orphan=scoring_deferred_orphan,
        embedded_assessment_vacancy_ids=embedded_assessment_vacancy_ids,
        hh_vacancy_ids=hh_vacancy_ids,
        source_counts=source_counts,
        deferred_counts=deferred_counts,
    )
