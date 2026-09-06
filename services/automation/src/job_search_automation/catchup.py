"""Startup catch-up: at most one missed-interval recovery cycle."""

from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any, Callable

from job_search_automation.clients import CoreClient, HhClient, HttpError, ScoringClient
from job_search_automation.config import Settings
from job_search_automation.cycle import run_cycle
from job_search_automation.state import AutomationStateStore, parse_iso, utc_now, utc_now_iso

logger = logging.getLogger("job_search_automation.catchup")


def should_startup_catchup(state: dict[str, Any], *, now=None) -> bool:
    """Return True when enabled automation missed its next_run_at while down.

    Rule: ``enabled`` and ``next_run_at <= now``. Multiple missed hours still
    produce a single True — callers run exactly one cycle, then schedule
    ``now + interval`` (not one cycle per missed slot).

    No catch-up when disabled, or when ``next_run_at`` is missing/future
    (ordinary restart inside the open interval).
    """
    if not state.get("enabled"):
        return False
    next_run = parse_iso(state.get("next_run_at"))
    if next_run is None:
        return False
    clock = now or utc_now()
    return next_run <= clock


def wait_dependencies(
    *,
    core: CoreClient,
    hh: HhClient,
    scoring: ScoringClient,
    timeout_seconds: float = 300.0,
    poll_seconds: float = 5.0,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Poll cheap health endpoints until ready or timeout (no busy-loop spin)."""
    poll = max(1.0, poll_seconds)
    max_attempts = max(1, int(timeout_seconds / poll) + 1)
    last_error = "dependencies_not_ready"
    for _attempt in range(max_attempts):
        errors: list[str] = []
        try:
            core.health_ready()
        except HttpError as error:
            errors.append(f"core:{error.code}")
        try:
            hh.health_ready()
        except HttpError as error:
            # HH degraded (session) still returns payload; health_ready raises on 5xx.
            errors.append(f"hh:{error.code}")
        try:
            scoring.health_ready()
        except HttpError as error:
            errors.append(f"scoring:{error.code}")
        if not errors:
            return {"ok": True, "error": None}
        last_error = ",".join(errors)
        if _attempt + 1 >= max_attempts:
            break
        sleeper(poll)
    return {"ok": False, "error": last_error}


def maybe_startup_catchup(
    *,
    settings: Settings,
    store: AutomationStateStore,
    core: CoreClient,
    hh: HhClient,
    scoring: ScoringClient,
    dependency_timeout_seconds: float = 300.0,
) -> dict[str, Any]:
    """Run at most one catch-up cycle using the canonical ``run_cycle`` path."""
    state = store.load()
    if not should_startup_catchup(state):
        reason = "disabled" if not state.get("enabled") else "not_due"
        return {
            "performed": False,
            "reason": reason,
            "observed_at": utc_now_iso(),
            "next_run_at": state.get("next_run_at"),
        }

    deps = wait_dependencies(
        core=core,
        hh=hh,
        scoring=scoring,
        timeout_seconds=dependency_timeout_seconds,
    )
    if not deps.get("ok"):
        interval = int(state.get("interval_seconds") or settings.interval_seconds)

        def _record(s: dict[str, Any]) -> None:
            s["last_error"] = f"startup_catchup_deps:{deps.get('error')}"
            s["last_status"] = "error"
            s["last_finished_at"] = utc_now_iso()
            s["next_run_at"] = (
                utc_now() + timedelta(seconds=max(60, interval))
            ).isoformat().replace("+00:00", "Z")

        store.update(_record)
        logger.warning("startup catch-up skipped: dependencies not ready (%s)", deps.get("error"))
        return {
            "performed": False,
            "reason": "dependencies_not_ready",
            "error": deps.get("error"),
            "observed_at": utc_now_iso(),
            "state": store.load(),
        }

    logger.info("automation startup catch-up → run_cycle (single)")
    result = run_cycle(
        settings=settings,
        store=store,
        core=core,
        hh=hh,
        scoring=scoring,
        trigger="startup_catchup",
    )
    result["performed"] = result.get("status") != "skipped_already_running"
    result["reason"] = "missed_next_run_at"
    return result
