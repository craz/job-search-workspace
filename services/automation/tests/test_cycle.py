"""Unit tests for automation cycle selection, lock, and API controls."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from job_search_automation.app import create_app
from job_search_automation.clients import HttpError
from job_search_automation.config import Settings
from job_search_automation.cycle import run_cycle, select_cycle_score_candidates
from job_search_automation.state import AutomationStateStore


def _settings(state_dir: Path, **overrides: object) -> Settings:
    base = dict(
        core_base_url="http://core.test",
        hh_base_url="http://hh.test",
        scoring_base_url="http://scoring.test",
        state_dir=state_dir,
        http_port=8095,
        interval_seconds=3600,
        max_enqueue_per_cycle=2,
        lock_ttl_seconds=7200,
        auto_score_max_age_days=14,
        default_enabled=False,
        suitable_max_pages=1,
        http_timeout_seconds=30.0,
    )
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


class SelectCycleCandidatesTests(unittest.TestCase):
    def test_only_created_updated_never_scored_active_fresh(self) -> None:
        items = [
            {"outcome": "unchanged", "vacancy_id": "old-backlog"},
            {"outcome": "created", "vacancy_id": "new-1"},
            {"outcome": "updated", "vacancy_id": "upd-1"},
            {"outcome": "created", "vacancy_id": "skipped-owner"},
            {"outcome": "created", "vacancy_id": "already-scored"},
            {"outcome": "created", "vacancy_id": "new-2"},
            {"outcome": "created", "vacancy_id": "new-3"},
        ]
        vacancies = {
            "new-1": {
                "id": "new-1",
                "owner_decision": "unreviewed",
                "source_status": "active",
                "source_published_at": "2026-09-06T00:00:00Z",
            },
            "upd-1": {
                "id": "upd-1",
                "owner_decision": "interested",
                "source_status": "active",
                "source_published_at": "2026-09-05T00:00:00Z",
            },
            "skipped-owner": {
                "id": "skipped-owner",
                "owner_decision": "skipped",
                "source_status": "active",
                "source_published_at": "2026-09-06T00:00:00Z",
            },
            "already-scored": {
                "id": "already-scored",
                "owner_decision": "unreviewed",
                "source_status": "active",
                "source_published_at": "2026-09-06T00:00:00Z",
            },
            "new-2": {
                "id": "new-2",
                "owner_decision": "unreviewed",
                "source_status": "active",
                "source_published_at": "2026-09-06T00:00:00Z",
            },
            "new-3": {
                "id": "new-3",
                "owner_decision": "unreviewed",
                "source_status": "active",
                "source_published_at": "2026-09-06T00:00:00Z",
            },
        }
        states = {
            "new-1": {"state": "never_scored"},
            "upd-1": {"state": "never_scored"},
            "skipped-owner": {"state": "never_scored"},
            "already-scored": {"state": "current"},
            "new-2": {"state": "never_scored"},
            "new-3": {"state": "never_scored"},
        }
        selected, stats = select_cycle_score_candidates(
            items,
            fetch_vacancy=lambda vid: vacancies[vid],
            fetch_scoring_state=lambda vid: states[vid],
            max_enqueue=2,
            max_age_days=14,
        )
        self.assertEqual(selected, ["new-1", "upd-1"])
        self.assertEqual(stats["scoring_candidates"], 4)  # new-1, upd-1, new-2, new-3
        self.assertEqual(stats["scoring_pending_next_cycle"], 2)
        self.assertGreaterEqual(stats["scoring_skipped"], 2)
        self.assertNotIn("old-backlog", selected)

    def test_does_not_mutate_owner_decision(self) -> None:
        # Selection only reads vacancy; no write client involved.
        items = [{"outcome": "created", "vacancy_id": "v1"}]
        vacancy = {
            "id": "v1",
            "owner_decision": "unreviewed",
            "source_status": "active",
            "source_published_at": "2026-09-06T00:00:00Z",
        }
        selected, _ = select_cycle_score_candidates(
            items,
            fetch_vacancy=lambda _vid: vacancy,
            fetch_scoring_state=lambda _vid: {"state": "never_scored"},
            max_enqueue=5,
            max_age_days=14,
        )
        self.assertEqual(selected, ["v1"])
        self.assertEqual(vacancy["owner_decision"], "unreviewed")


class LockAndApiTests(unittest.TestCase):
    def test_overlap_run_now_skipped(self) -> None:
        with TemporaryDirectory() as tmp:
            settings = _settings(Path(tmp))
            store = AutomationStateStore(settings.state_path, lock_ttl_seconds=7200)
            ok, _ = store.try_acquire_lock(holder="cycle-a")
            self.assertTrue(ok)
            core = MagicMock()
            hh = MagicMock()
            scoring = MagicMock()
            result = run_cycle(
                settings=settings,
                store=store,
                core=core,
                hh=hh,
                scoring=scoring,
                trigger="run_now",
            )
            self.assertEqual(result["status"], "skipped_already_running")
            hh.run_suitable.assert_not_called()
            scoring.enqueue_semantic_v1.assert_not_called()

    def test_enable_disable_and_status_api(self) -> None:
        with TemporaryDirectory() as tmp:
            settings = _settings(Path(tmp))
            app = create_app(settings)
            client = TestClient(app)
            status = client.get("/api/v1/automation/status").json()
            self.assertFalse(status["enabled"])
            self.assertEqual(status["last_status"], "never_run")
            enabled = client.post(
                "/api/v1/automation/enable", json={"enabled": True}
            ).json()
            self.assertTrue(enabled["enabled"])
            self.assertIsNotNone(enabled["next_run_at"])
            disabled = client.post(
                "/api/v1/automation/enable", json={"enabled": False}
            ).json()
            self.assertFalse(disabled["enabled"])
            self.assertIsNone(disabled["next_run_at"])

    def test_restart_recovers_stale_lock(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "automation_state.json"
            store = AutomationStateStore(path, lock_ttl_seconds=1)
            store.save(
                {
                    **store.load(),
                    "running": True,
                    "lock": {
                        "holder": "dead",
                        "acquired_at": "2020-01-01T00:00:00Z",
                        "expires_at": "2020-01-01T00:01:00Z",
                    },
                    "last_status": "running",
                }
            )
            # New store instance simulates process restart.
            restarted = AutomationStateStore(path, lock_ttl_seconds=1)
            state = restarted.recover_after_process_start()
            self.assertFalse(state["running"])
            self.assertIsNone(state["lock"])
            acquired, _ = restarted.try_acquire_lock(holder="after-restart")
            self.assertTrue(acquired)

    def test_restart_clears_unexpired_running_lock(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "automation_state.json"
            store = AutomationStateStore(path, lock_ttl_seconds=7200)
            ok, _ = store.try_acquire_lock(holder="killed-process")
            self.assertTrue(ok)
            restarted = AutomationStateStore(path, lock_ttl_seconds=7200)
            state = restarted.recover_after_process_start()
            self.assertFalse(state["running"])
            self.assertEqual(state["last_error"], "interrupted_by_restart")
            acquired, _ = restarted.try_acquire_lock(holder="fresh")
            self.assertTrue(acquired)

    def test_run_now_does_not_call_backlog_enqueue(self) -> None:
        with TemporaryDirectory() as tmp:
            settings = _settings(Path(tmp), max_enqueue_per_cycle=5)
            store = AutomationStateStore(settings.state_path)
            core = MagicMock()
            hh = MagicMock()
            scoring = MagicMock()
            core.health_ready.return_value = None
            hh.health_ready.return_value = {"status": "ok"}
            scoring.health_ready.return_value = None
            hh.run_suitable.return_value = {
                "search_run": {
                    "id": "sr-1",
                    "status": "success",
                    "source_total": 3,
                },
                "source_total": 3,
            }
            core.search_run_items.return_value = [
                {"outcome": "created", "vacancy_id": "v-new"},
                {"outcome": "unchanged", "vacancy_id": "v-old"},
            ]
            core.vacancy.return_value = {
                "id": "v-new",
                "owner_decision": "unreviewed",
                "source_status": "active",
                "source_published_at": "2026-09-06T12:00:00Z",
            }
            scoring.scoring_state.return_value = {"state": "never_scored"}
            scoring.enqueue_semantic_v1.return_value = {
                "job_id": "job-1",
                "status": "queued",
            }
            result = run_cycle(
                settings=settings,
                store=store,
                core=core,
                hh=hh,
                scoring=scoring,
                trigger="run_now",
            )
            self.assertTrue(result["ok"])
            self.assertEqual(result["cycle"]["scoring_enqueued"], 1)
            self.assertEqual(result["cycle"]["unchanged"], 1)
            scoring.enqueue_semantic_v1.assert_called_once_with("v-new")
            self.assertEqual(scoring.method_calls[0][0], "health_ready")

    def test_failure_releases_lock(self) -> None:
        with TemporaryDirectory() as tmp:
            settings = _settings(Path(tmp))
            store = AutomationStateStore(settings.state_path)
            core = MagicMock()
            hh = MagicMock()
            scoring = MagicMock()
            core.health_ready.side_effect = HttpError("core_unhealthy", "down")
            result = run_cycle(
                settings=settings,
                store=store,
                core=core,
                hh=hh,
                scoring=scoring,
                trigger="run_now",
            )
            self.assertEqual(result["status"], "error")
            state = store.load()
            self.assertFalse(state["running"])
            self.assertIsNone(state["lock"])
            self.assertIn("core_unhealthy", state["last_error"] or "")


if __name__ == "__main__":
    unittest.main()
