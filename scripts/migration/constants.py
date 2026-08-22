"""Locked migration constants for the first supported legacy import slice."""

from __future__ import annotations

from pathlib import Path

DEFAULT_LEGACY_ROOT = Path("/data/Projects/job_search")

SOURCE_HH = "hh"
SOURCE_LEGACY = "legacy_job_search"
SOURCE_SCORING = "legacy_job_search_scoring"

# Migration sentinel — NOT a historical prompt/policy version (DATA-00.3 §23.14).
PROMPT_VERSION_SENTINEL = "legacy_job_search:import"

# Canonical HH vacancy page URL — matches legacy `/vacancy/{id}` convention (DATA_MIGRATION §5).
HH_VACANCY_URL_TEMPLATE = "https://hh.ru/vacancy/{vacancy_id}"

MODE_DRY_RUN = "DRY_RUN"

EXPECTED_ELIGIBLE_COUNTS: dict[str, int] = {
    "companies": 323,
    "vacancies": 452,  # 499 with company_id minus 47 company_track rows without reconstructable vacancy URL
    "applications": 407,
    "people": 24,
    "daily_metrics": 81,
    "hypotheses": 2,
}

EXPECTED_DEFERRED_COUNTS: dict[str, int] = {
    "watch_only_companies": 1043,
    "orphan_vacancies": 12,
    "vacancies_missing_url": 47,
    "embedded_assessments": 16,
    "off_db_scored_vacancies": 850,
}

MAX_ELIGIBLE_ASSESSMENTS = 20

VACANCY_STATUS_MAP: dict[str, str] = {
    "found": "new",
    "viewed": "reviewing",
    "prioritized": "shortlisted",
    "applied": "reviewing",
    "interview": "shortlisted",
    "reject": "rejected",
    "archived": "rejected",
}

APPLICATION_RESULT_MAP: dict[str, str | None] = {
    "reply": "reply",
    "interview": "interview",
    "rejected": "rejected",
    "offer": "offer",
}

ASSESSMENT_ACTION_MAP: dict[str, str] = {
    "apply": "apply",
    "maybe": "review",
    "skip": "skip",
}

PERSON_SOURCE_NORMALIZE: dict[str, str] = {
    "company_site": SOURCE_LEGACY,
}
