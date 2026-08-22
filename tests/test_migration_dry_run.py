"""Tests for PB-DATA-00.4 legacy migration dry-run tooling."""

from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parent.parent
LEGACY_ROOT = Path("/data/Projects/job_search")
CORE_SRC = ROOT / "services/core/src"

import sys

sys.path[:0] = [str(ROOT), str(CORE_SRC)]

from job_search_core.models import (  # noqa: E402
    Application,
    ApplicationResult,
    Assessment,
    AssessmentVerdict,
    Base,
    Company,
    DailyMetric,
    Hypothesis,
    HypothesisStatus,
    Person,
    PersonRole,
    PersonStatus,
    Vacancy,
    VacancyStatus,
)

from scripts.migration.constants import (  # noqa: E402
    EXPECTED_ELIGIBLE_COUNTS,
    PROMPT_VERSION_SENTINEL,
    SOURCE_LEGACY,
    SOURCE_SCORING,
)
from scripts.migration.dry_run import run_dry_run  # noqa: E402
from scripts.migration.equivalence import records_equivalent  # noqa: E402
from scripts.migration.fingerprint import build_source_fingerprint, fingerprint_file, fingerprints_equal  # noqa: E402
from scripts.migration.source_reader import _connect_readonly, load_legacy_snapshot  # noqa: E402
from scripts.migration.target_inspect import read_only_target_session, target_row_counts  # noqa: E402
from scripts.migration.transform import (  # noqa: E402
    transform_applications,
    transform_assessments,
    transform_companies,
    transform_daily_metrics,
    transform_snapshot,
    transform_vacancies,
)
from scripts.migration.types import LegacyAnomaly  # noqa: E402
from scripts.migration.validation import collect_validation_issues  # noqa: E402


def create_sqlite_target() -> str:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return "sqlite+pysqlite://"


@unittest.skipUnless(LEGACY_ROOT.joinpath("data/job_search.db").exists(), "legacy source unavailable")
class LegacySourceIntegrationTests(unittest.TestCase):
    """Validate mapping against the real read-only legacy archive."""

    def test_source_reader_is_read_only(self) -> None:
        db_path = LEGACY_ROOT / "data/job_search.db"
        connection = _connect_readonly(db_path)
        with self.assertRaises(sqlite3.OperationalError):
            connection.execute("UPDATE companies SET name = name WHERE 0")
        connection.close()

    def test_real_legacy_counts_match_contract(self) -> None:
        snapshot = load_legacy_snapshot(LEGACY_ROOT)
        self.assertEqual(snapshot.source_counts["companies_referenced"], 323)
        self.assertEqual(snapshot.source_counts["vacancies_with_company"], 499)
        self.assertEqual(snapshot.source_counts["vacancies_without_company"], 12)
        self.assertEqual(snapshot.source_counts["applications"], 407)
        self.assertEqual(len(snapshot.watch_only_companies), 1043)
        self.assertEqual(len(snapshot.scoring_rows), 19)
        self.assertEqual(len(snapshot.scoring_deferred_orphan), 1)
        self.assertEqual(len(snapshot.scoring_deferred_history), 1)

    def test_company_and_vacancy_mapping(self) -> None:
        snapshot = load_legacy_snapshot(LEGACY_ROOT)
        companies = transform_companies(snapshot)
        vacancies = transform_vacancies(snapshot)
        self.assertEqual(len(companies), 323)
        self.assertEqual(len(vacancies), 499)
        self.assertTrue(any(item.identity.source == "hh" for item in companies))
        self.assertTrue(any(item.identity.source == SOURCE_LEGACY for item in vacancies))

    def test_orphan_vacancies_are_deferred_not_planned(self) -> None:
        snapshot = load_legacy_snapshot(LEGACY_ROOT)
        planned = transform_vacancies(snapshot)
        planned_ids = {item.identity.legacy_key for item in planned}
        for row in snapshot.orphan_vacancies:
            self.assertNotIn(f"vacancy:{row['id']}", planned_ids)

    def test_application_autoreply_anomaly(self) -> None:
        snapshot = load_legacy_snapshot(LEGACY_ROOT)
        anomalies: list[LegacyAnomaly] = []
        applications = transform_applications(snapshot, anomalies=anomalies)
        autoreply = next(item for item in applications if item.identity.external_id == "application-3")
        self.assertIsNone(autoreply.payload["result"])
        self.assertEqual(anomalies[0].code, "legacy_result_autoreply")

    def test_daily_metrics_include_all_81_rows(self) -> None:
        snapshot = load_legacy_snapshot(LEGACY_ROOT)
        metrics = transform_daily_metrics(snapshot)
        self.assertEqual(len(metrics), 81)
        self.assertLess(
            min(datetime.fromisoformat(item.payload["metric_date"]).date().isoformat() for item in metrics),
            "2026-06-04",
        )

    def test_assessment_latest_and_sentinel(self) -> None:
        snapshot = load_legacy_snapshot(LEGACY_ROOT)
        assessments = transform_assessments(snapshot)
        self.assertLessEqual(len(assessments), 20)
        self.assertEqual(len(assessments), 19)
        first = assessments[0]
        self.assertEqual(first.identity.source, SOURCE_SCORING)
        self.assertEqual(first.payload["prompt_version"], PROMPT_VERSION_SENTINEL)
        self.assertTrue(first.payload["model"].startswith("legacy:"))

    def test_deferred_off_db_scores_not_planned(self) -> None:
        snapshot = load_legacy_snapshot(LEGACY_ROOT)
        planned = {item.identity.external_id for item in transform_assessments(snapshot)}
        for record in snapshot.scoring_deferred_off_db[:5]:
            hh_id = str((record.get("score") or {}).get("vacancy_id"))
            self.assertNotIn(hh_id, planned)


class MigrationDryRunBehaviorTests(unittest.TestCase):
    """Synthetic tests for validation, equivalence and zero-mutation guarantees."""

    def test_fingerprint_change_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            data.mkdir()
            db = data / "job_search.db"
            jsonl = data / "vacancy_scores.jsonl"
            shutil.copy2(LEGACY_ROOT / "data/job_search.db", db)
            shutil.copy2(LEGACY_ROOT / "data/vacancy_scores.jsonl", jsonl)
            first = build_source_fingerprint(root)
            jsonl.write_text(jsonl.read_text() + "\n", encoding="utf-8")
            second = build_source_fingerprint(root)
            self.assertFalse(fingerprints_equal(first, second))

    def test_unknown_enum_is_fatal(self) -> None:
        snapshot = load_legacy_snapshot(LEGACY_ROOT)
        snapshot.vacancies[0]["status"] = "totally-unknown"
        with self.assertRaises(ValueError):
            transform_vacancies(snapshot)

    def test_duplicate_identity_detection(self) -> None:
        snapshot = load_legacy_snapshot(LEGACY_ROOT)
        planned = transform_snapshot(snapshot, anomalies=[])
        duplicate = planned["companies"][0]
        planned["companies"].append(duplicate)
        issues = collect_validation_issues(snapshot, planned)
        self.assertTrue(any(issue.code == "duplicate_planned_identity" for issue in issues))

    def test_existing_equivalent_and_conflict(self) -> None:
        snapshot = load_legacy_snapshot(LEGACY_ROOT)
        company = transform_companies(snapshot)[0]
        with read_only_target_session(create_sqlite_target()) as session:
            session.add(
                Company(
                    name=company.payload["name"],
                    source=company.payload["source"],
                    external_id=company.payload["external_id"],
                    website_url=company.payload.get("website_url"),
                )
            )
            session.flush()
            existing = {
                "name": company.payload["name"],
                "source": company.payload["source"],
                "external_id": company.payload["external_id"],
                "website_url": company.payload.get("website_url"),
            }
            self.assertTrue(records_equivalent("companies", company.payload, existing))
            different = dict(existing)
            different["name"] = "Different Name"
            self.assertFalse(records_equivalent("companies", company.payload, different))

    def test_dry_run_writes_reports_without_target_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "runs"
            run_dir, before, after, success = run_dry_run(
                workspace_root=ROOT,
                legacy_root=LEGACY_ROOT,
                target_database_url=create_sqlite_target(),
                output_root=output,
            )
            self.assertTrue((run_dir / "dry-run-report.json").exists())
            self.assertTrue((run_dir / "dry-run-report.md").exists())
            self.assertTrue((run_dir / "source-fingerprint.json").exists())
            self.assertEqual(before, after)
            report = json.loads((run_dir / "dry-run-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["mode"], "DRY_RUN")
            self.assertEqual(report["counts"]["companies"]["eligible"], 323)
            self.assertEqual(report["counts"]["assessments"]["eligible"], 19)
            self.assertIn(PROMPT_VERSION_SENTINEL, "\n".join(report["notes"]))
            self.assertTrue(success)


if __name__ == "__main__":
    unittest.main()
