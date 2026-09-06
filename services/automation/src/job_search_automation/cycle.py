"""One automation cycle: HH suitable → cycle-scoped score enqueue."""

from __future__ import annotations

import uuid
from typing import Any, Callable

from job_search_automation.clients import CoreClient, HhClient, HttpError, ScoringClient
from job_search_automation.config import Settings
from job_search_automation.freshness import evaluate_freshness
from job_search_automation.state import (
    AutomationStateStore,
    empty_cycle_counts,
    utc_now_iso,
)

OWNER_DECISIONS_BLOCK_AUTO_SCORE = frozenset({"skipped", "applied"})
CYCLE_SCORE_OUTCOMES = frozenset({"created", "updated"})


class CycleAlreadyRunning(RuntimeError):
    """Raised when a second overlapping cycle is requested."""


def _count_outcomes(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"created": 0, "updated": 0, "unchanged": 0, "errors": 0, "processed": 0}
    for item in items:
        outcome = str(item.get("outcome") or "").lower()
        counts["processed"] += 1
        if outcome in counts:
            counts[outcome] += 1
        elif outcome == "error":
            counts["errors"] += 1
    return counts


def select_cycle_score_candidates(
    items: list[dict[str, Any]],
    *,
    fetch_vacancy: Callable[[str], dict[str, Any]],
    fetch_scoring_state: Callable[[str], dict[str, Any]],
    max_enqueue: int,
    max_age_days: int,
) -> tuple[list[str], dict[str, int]]:
    """Select vacancy IDs from THIS SearchRun only (created/updated), with eligibility.

    Does not scan historical never_scored backlog.
    """
    stats = {
        "scoring_candidates": 0,
        "scoring_skipped": 0,
        "scoring_deferred": 0,
        "scoring_pending_next_cycle": 0,
    }
    selected: list[str] = []
    for item in items:
        outcome = str(item.get("outcome") or "").lower()
        if outcome not in CYCLE_SCORE_OUTCOMES:
            continue
        vacancy_id = str(item.get("vacancy_id") or "").strip()
        if not vacancy_id:
            stats["scoring_skipped"] += 1
            continue
        try:
            vacancy = fetch_vacancy(vacancy_id)
        except HttpError:
            stats["scoring_deferred"] += 1
            continue
        owner = str(vacancy.get("owner_decision") or "unreviewed").lower()
        if owner in OWNER_DECISIONS_BLOCK_AUTO_SCORE:
            stats["scoring_skipped"] += 1
            continue
        source_status = str(vacancy.get("source_status") or "unknown").lower()
        if source_status != "active":
            stats["scoring_skipped"] += 1
            continue
        freshness = evaluate_freshness(vacancy, max_age_days=max_age_days)
        if freshness != "fresh":
            stats["scoring_skipped"] += 1
            continue
        try:
            scoring_state = fetch_scoring_state(vacancy_id)
        except HttpError:
            stats["scoring_deferred"] += 1
            continue
        state = str(scoring_state.get("state") or "").lower()
        if state != "never_scored":
            stats["scoring_skipped"] += 1
            continue
        stats["scoring_candidates"] += 1
        if len(selected) >= max_enqueue:
            stats["scoring_pending_next_cycle"] += 1
            continue
        selected.append(vacancy_id)
    return selected, stats


def run_cycle(
    *,
    settings: Settings,
    store: AutomationStateStore,
    core: CoreClient,
    hh: HhClient,
    scoring: ScoringClient,
    trigger: str = "schedule",
) -> dict[str, Any]:
    """Execute one automation cycle. Overlap returns skipped_already_running."""
    # Use persisted operator overrides for bounds/interval.
    live = store.load()
    max_enqueue = int(live.get("max_enqueue_per_cycle") or settings.max_enqueue_per_cycle)
    interval_seconds = int(live.get("interval_seconds") or settings.interval_seconds)

    acquired, _ = store.try_acquire_lock(holder=f"{trigger}:{uuid.uuid4().hex[:8]}")
    if not acquired:
        state = store.load()
        return {
            "ok": False,
            "status": "skipped_already_running",
            "message": "Automation cycle already running",
            "state": state,
        }

    cycle = empty_cycle_counts()
    cycle["cycle_id"] = str(uuid.uuid4())
    try:
        core.health_ready()
        hh.health_ready()
        scoring.health_ready()

        suitable = hh.run_suitable(max_pages=settings.suitable_max_pages)
        search_run = suitable.get("search_run") if isinstance(suitable.get("search_run"), dict) else {}
        search_run_id = str(
            (search_run or {}).get("id") or suitable.get("search_run_id") or ""
        ).strip()
        cycle["search_run_id"] = search_run_id or None
        cycle["source_total"] = suitable.get("source_total")
        if cycle["source_total"] is None and search_run:
            cycle["source_total"] = search_run.get("source_total")

        run_status = str((search_run or {}).get("status") or suitable.get("status") or "")
        error_code = (search_run or {}).get("error_code") or suitable.get("code")
        if run_status == "failed" or (error_code and not search_run_id):
            message = str(
                (search_run or {}).get("error_message")
                or suitable.get("message")
                or error_code
                or "hh_suitable_failed"
            )
            state = store.release_lock(
                status="error",
                error=str(error_code or message),
                last_cycle=cycle,
                schedule_next=True,
                interval_seconds=interval_seconds,
            )
            return {
                "ok": False,
                "status": "error",
                "message": message,
                "code": error_code,
                "requires_user_action": str(error_code or "")
                in {
                    "not_authorized",
                    "action_required",
                    "captcha",
                    "session_expired",
                    "browser_proxy_unavailable",
                },
                "state": state,
                "cycle": cycle,
            }

        items: list[dict[str, Any]] = []
        if search_run_id:
            items = core.search_run_items(search_run_id)
        outcome_counts = _count_outcomes(items)
        cycle.update(outcome_counts)

        selected, score_stats = select_cycle_score_candidates(
            items,
            fetch_vacancy=core.vacancy,
            fetch_scoring_state=scoring.scoring_state,
            max_enqueue=max_enqueue,
            max_age_days=settings.auto_score_max_age_days,
        )
        cycle.update(score_stats)

        job_ids: list[str] = []
        for vacancy_id in selected:
            try:
                result = scoring.enqueue_semantic_v1(vacancy_id)
            except HttpError as error:
                if error.code in {"already_queued", "active_queue_duplicate"}:
                    cycle["scoring_skipped"] = int(cycle["scoring_skipped"]) + 1
                    continue
                if error.code in {
                    "blocked",
                    "needs_lifecycle_refresh",
                    "vacancy_source_archived",
                    "vacancy_source_status_unknown",
                }:
                    cycle["scoring_skipped"] = int(cycle["scoring_skipped"]) + 1
                    continue
                cycle["scoring_deferred"] = int(cycle["scoring_deferred"]) + 1
                continue
            if result.get("reused_existing") or result.get("status") == "done":
                cycle["scoring_skipped"] = int(cycle["scoring_skipped"]) + 1
                continue
            job_id = str(result.get("job_id") or "")
            if job_id:
                job_ids.append(job_id)
                cycle["scoring_enqueued"] = int(cycle["scoring_enqueued"]) + 1
            else:
                cycle["scoring_deferred"] = int(cycle["scoring_deferred"]) + 1
        cycle["job_ids"] = job_ids

        state = store.release_lock(
            status="ok",
            error=None,
            last_cycle=cycle,
            schedule_next=True,
            interval_seconds=interval_seconds,
        )
        return {
            "ok": True,
            "status": "ok",
            "message": "cycle completed; scoring jobs enqueued for worker",
            "trigger": trigger,
            "finished_at": utc_now_iso(),
            "state": state,
            "cycle": cycle,
        }
    except HttpError as error:
        state = store.release_lock(
            status="error",
            error=f"{error.code}:{error.message}",
            last_cycle=cycle,
            schedule_next=True,
            interval_seconds=interval_seconds,
        )
        return {
            "ok": False,
            "status": "error",
            "message": error.message,
            "code": error.code,
            "state": state,
            "cycle": cycle,
        }
    except Exception as error:  # noqa: BLE001 - cycle must always release lock
        state = store.release_lock(
            status="error",
            error=str(error)[:500],
            last_cycle=cycle,
            schedule_next=True,
            interval_seconds=interval_seconds,
        )
        return {
            "ok": False,
            "status": "error",
            "message": str(error)[:500],
            "state": state,
            "cycle": cycle,
        }
