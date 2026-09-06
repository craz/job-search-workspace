"""Persisted automation status, config toggles, and single-host lock."""

from __future__ import annotations

import json
import os
import threading
import uuid
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

_LOCK = threading.RLock()


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def utc_now_iso() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def empty_cycle_counts() -> dict[str, Any]:
    return {
        "source_total": None,
        "processed": 0,
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "errors": 0,
        "scoring_candidates": 0,
        "scoring_enqueued": 0,
        "scoring_skipped": 0,
        "scoring_deferred": 0,
        "scoring_pending_next_cycle": 0,
        "job_ids": [],
        "search_run_id": None,
        "cycle_id": None,
    }


def default_state(
    *,
    enabled: bool = False,
    interval_seconds: int = 3600,
    max_enqueue_per_cycle: int = 20,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "enabled": enabled,
        "interval_seconds": interval_seconds,
        "max_enqueue_per_cycle": max_enqueue_per_cycle,
        "running": False,
        "lock": None,
        "last_started_at": None,
        "last_finished_at": None,
        "last_status": "never_run",
        "last_error": None,
        "next_run_at": None,
        "last_cycle": empty_cycle_counts(),
    }


class AutomationStateStore:
    """JSON file store with process-local mutex (single-user Compose service)."""

    def __init__(self, path: Path, *, lock_ttl_seconds: int = 7200) -> None:
        self.path = path
        self.lock_ttl_seconds = lock_ttl_seconds
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read_unlocked(self) -> dict[str, Any]:
        if not self.path.is_file():
            return default_state()
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return default_state()
        base = default_state()
        base.update(raw)
        if not isinstance(base.get("last_cycle"), dict):
            base["last_cycle"] = empty_cycle_counts()
        return base

    def _write_unlocked(self, state: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp, self.path)

    def load(self) -> dict[str, Any]:
        with _LOCK:
            state = self._read_unlocked()
            self._recover_stale_lock_unlocked(state)
            return deepcopy(state)

    def save(self, state: dict[str, Any]) -> dict[str, Any]:
        with _LOCK:
            self._write_unlocked(state)
            return deepcopy(state)

    def update(self, mutator) -> dict[str, Any]:  # noqa: ANN001
        with _LOCK:
            state = self._read_unlocked()
            self._recover_stale_lock_unlocked(state)
            mutator(state)
            self._write_unlocked(state)
            return deepcopy(state)

    def _recover_stale_lock_unlocked(self, state: dict[str, Any]) -> None:
        lock = state.get("lock")
        if not isinstance(lock, dict):
            if state.get("running"):
                state["running"] = False
                self._write_unlocked(state)
            return
        expires = parse_iso(str(lock.get("expires_at") or ""))
        now = utc_now()
        if expires is None or expires <= now:
            state["lock"] = None
            state["running"] = False
            if state.get("last_status") == "running":
                state["last_status"] = "error"
                state["last_error"] = "lock_expired_after_restart_or_crash"
                state["last_finished_at"] = utc_now_iso()
            self._write_unlocked(state)

    def recover_after_process_start(self) -> dict[str, Any]:
        """Clear in-process lock left by a previous container/process crash.

        Single-user Compose service: a new process never inherits the previous
        asyncio cycle, so any persisted ``running`` lock is stale immediately.
        """
        with _LOCK:
            state = self._read_unlocked()
            if state.get("running") or state.get("lock"):
                state["lock"] = None
                state["running"] = False
                if state.get("last_status") == "running":
                    state["last_status"] = "error"
                    state["last_error"] = "interrupted_by_restart"
                    state["last_finished_at"] = utc_now_iso()
                self._write_unlocked(state)
            else:
                self._recover_stale_lock_unlocked(state)
            return deepcopy(state)

    def try_acquire_lock(self, *, holder: str | None = None) -> tuple[bool, dict[str, Any]]:
        """Acquire singleton cycle lock. Returns (acquired, state)."""
        with _LOCK:
            state = self._read_unlocked()
            self._recover_stale_lock_unlocked(state)
            if state.get("running") or state.get("lock"):
                return False, deepcopy(state)
            now = utc_now()
            token = holder or f"{os.getpid()}:{uuid.uuid4().hex[:8]}"
            state["lock"] = {
                "holder": token,
                "acquired_at": now.isoformat().replace("+00:00", "Z"),
                "expires_at": (now + timedelta(seconds=self.lock_ttl_seconds))
                .isoformat()
                .replace("+00:00", "Z"),
            }
            state["running"] = True
            state["last_started_at"] = state["lock"]["acquired_at"]
            state["last_status"] = "running"
            state["last_error"] = None
            self._write_unlocked(state)
            return True, deepcopy(state)

    def release_lock(
        self,
        *,
        status: str,
        error: str | None = None,
        last_cycle: dict[str, Any] | None = None,
        schedule_next: bool = False,
        interval_seconds: int | None = None,
    ) -> dict[str, Any]:
        with _LOCK:
            state = self._read_unlocked()
            state["lock"] = None
            state["running"] = False
            state["last_finished_at"] = utc_now_iso()
            state["last_status"] = status
            state["last_error"] = error
            if last_cycle is not None:
                state["last_cycle"] = last_cycle
            if schedule_next and state.get("enabled"):
                interval = int(interval_seconds or state.get("interval_seconds") or 3600)
                state["next_run_at"] = (
                    utc_now() + timedelta(seconds=max(60, interval))
                ).isoformat().replace("+00:00", "Z")
            elif not state.get("enabled"):
                state["next_run_at"] = None
            self._write_unlocked(state)
            return deepcopy(state)
