"""Unit tests for startup catch-up rules (R2.5.3A)."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from job_search_automation.catchup import (
    maybe_startup_catchup,
    should_startup_catchup,
    wait_dependencies,
)
from job_search_automation.clients import HttpError
from job_search_automation.config import Settings
from job_search_automation.state import AutomationStateStore


def _settings(state_dir: Path) -> Settings:
    return Settings(
        core_base_url="http://core.test",
        hh_base_url="http://hh.test",
        scoring_base_url="http://scoring.test",
        state_dir=state_dir,
        http_port=8095,
        interval_seconds=3600,
        max_enqueue_per_cycle=5,
        lock_ttl_seconds=7200,
        auto_score_max_age_days=14,
        default_enabled=False,
        suitable_max_pages=1,
        http_timeout_seconds=30.0,
    )


class CatchupRuleTests(unittest.TestCase):
    def test_disabled_no_catchup(self) -> None:
        self.assertFalse(
            should_startup_catchup(
                {
                    "enabled": False,
                    "next_run_at": "2020-01-01T00:00:00Z",
                }
            )
        )

    def test_future_next_run_no_catchup(self) -> None:
        future = (datetime.now(UTC) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
        self.assertFalse(
            should_startup_catchup({"enabled": True, "next_run_at": future})
        )

    def test_past_next_run_one_catchup_flag_even_if_many_hours(self) -> None:
        # Eight hours late still yields a single boolean True (one cycle).
        past = (datetime.now(UTC) - timedelta(hours=8)).isoformat().replace("+00:00", "Z")
        self.assertTrue(should_startup_catchup({"enabled": True, "next_run_at": past}))

    def test_missing_next_run_no_catchup(self) -> None:
        self.assertFalse(should_startup_catchup({"enabled": True, "next_run_at": None}))


class CatchupExecutionTests(unittest.TestCase):
    def test_deps_timeout_does_not_busy_loop(self) -> None:
        sleeps: list[float] = []
        core = MagicMock()
        hh = MagicMock()
        scoring = MagicMock()
        core.health_ready.side_effect = HttpError("core_unhealthy", "down")
        result = wait_dependencies(
            core=core,
            hh=hh,
            scoring=scoring,
            timeout_seconds=0.05,
            poll_seconds=1.0,
            sleeper=lambda s: sleeps.append(s),
        )
        self.assertFalse(result["ok"])
        self.assertEqual(len(sleeps), 0)  # single attempt when timeout < poll

    def test_maybe_catchup_disabled_skips(self) -> None:
        with TemporaryDirectory() as tmp:
            settings = _settings(Path(tmp))
            store = AutomationStateStore(settings.state_path)
            store.save({**store.load(), "enabled": False, "next_run_at": "2020-01-01T00:00:00Z"})
            result = maybe_startup_catchup(
                settings=settings,
                store=store,
                core=MagicMock(),
                hh=MagicMock(),
                scoring=MagicMock(),
            )
            self.assertFalse(result["performed"])
            self.assertEqual(result["reason"], "disabled")

    def test_maybe_catchup_calls_run_cycle_once(self) -> None:
        with TemporaryDirectory() as tmp:
            settings = _settings(Path(tmp))
            store = AutomationStateStore(settings.state_path)
            past = (datetime.now(UTC) - timedelta(hours=8)).isoformat().replace("+00:00", "Z")
            store.save(
                {
                    **store.load(),
                    "enabled": True,
                    "next_run_at": past,
                    "interval_seconds": 3600,
                }
            )
            core = MagicMock()
            hh = MagicMock()
            scoring = MagicMock()
            with patch("job_search_automation.catchup.run_cycle") as run_cycle:
                run_cycle.return_value = {
                    "ok": True,
                    "status": "ok",
                    "cycle": {"trigger": "startup_catchup"},
                }
                result = maybe_startup_catchup(
                    settings=settings,
                    store=store,
                    core=core,
                    hh=hh,
                    scoring=scoring,
                    dependency_timeout_seconds=1.0,
                )
            self.assertTrue(result["performed"])
            run_cycle.assert_called_once()
            self.assertEqual(run_cycle.call_args.kwargs["trigger"], "startup_catchup")


if __name__ == "__main__":
    unittest.main()
