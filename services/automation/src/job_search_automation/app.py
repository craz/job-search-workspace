"""FastAPI control plane + background interval scheduler for vacancy automation."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from job_search_automation.clients import CoreClient, HhClient, ScoringClient
from job_search_automation.config import Settings, load_settings
from job_search_automation.cycle import run_cycle
from job_search_automation.state import AutomationStateStore, parse_iso, utc_now, utc_now_iso

logger = logging.getLogger("job_search_automation")


class EnableRequest(BaseModel):
    enabled: bool


class ConfigPatch(BaseModel):
    interval_seconds: int | None = Field(default=None, ge=60)
    max_enqueue_per_cycle: int | None = Field(default=None, ge=1, le=100)


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or load_settings()
    store = AutomationStateStore(cfg.state_path, lock_ttl_seconds=cfg.lock_ttl_seconds)
    core = CoreClient(cfg.core_base_url, timeout_seconds=min(60.0, cfg.http_timeout_seconds))
    hh = HhClient(cfg.hh_base_url, timeout_seconds=cfg.http_timeout_seconds)
    scoring = ScoringClient(
        cfg.scoring_base_url, timeout_seconds=min(120.0, cfg.http_timeout_seconds)
    )

    # Seed persisted defaults once without enabling.
    def _ensure_state() -> dict[str, Any]:
        state = store.load()
        changed = False
        if "enabled" not in state:
            state["enabled"] = cfg.default_enabled
            changed = True
        if state.get("interval_seconds") in (None, 0):
            state["interval_seconds"] = cfg.interval_seconds
            changed = True
        if state.get("max_enqueue_per_cycle") in (None, 0):
            state["max_enqueue_per_cycle"] = cfg.max_enqueue_per_cycle
            changed = True
        # First boot: respect env default_enabled only when file was empty.
        if not cfg.state_path.is_file():
            state = store.save(
                {
                    **state,
                    "enabled": cfg.default_enabled,
                    "interval_seconds": cfg.interval_seconds,
                    "max_enqueue_per_cycle": cfg.max_enqueue_per_cycle,
                }
            )
            return state
        if changed:
            return store.save(state)
        return state

    _ensure_state()
    store.recover_after_process_start()

    async def _scheduler_loop() -> None:
        while True:
            try:
                state = store.load()
                if state.get("enabled") and not state.get("running"):
                    next_run = parse_iso(state.get("next_run_at"))
                    now = utc_now()
                    if next_run is None:
                        # Enabled but no next_run: schedule future, do not fire immediately.
                        interval = int(state.get("interval_seconds") or cfg.interval_seconds)

                        def _set_next(s: dict[str, Any]) -> None:
                            s["next_run_at"] = (
                                now + timedelta(seconds=max(60, interval))
                            ).isoformat().replace("+00:00", "Z")

                        store.update(_set_next)
                    elif next_run <= now:
                        logger.info("automation schedule tick → run_cycle")
                        await asyncio.to_thread(
                            run_cycle,
                            settings=cfg,
                            store=store,
                            core=core,
                            hh=hh,
                            scoring=scoring,
                            trigger="schedule",
                        )
            except Exception:  # noqa: BLE001
                logger.exception("automation scheduler tick failed")
            await asyncio.sleep(5)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        task = asyncio.create_task(_scheduler_loop())
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    application = FastAPI(title="Job Search Automation", lifespan=lifespan, docs_url="/docs")

    @application.get("/health/live")
    @application.get("/health/ready")
    def health() -> dict[str, str]:
        return {"status": "ok", "component": "job-search-automation"}

    @application.get("/api/v1/automation/status")
    def status() -> dict[str, Any]:
        state = store.load()
        return {
            "enabled": bool(state.get("enabled")),
            "running": bool(state.get("running")),
            "last_started_at": state.get("last_started_at"),
            "last_finished_at": state.get("last_finished_at"),
            "last_status": state.get("last_status"),
            "last_error": state.get("last_error"),
            "next_run_at": state.get("next_run_at"),
            "interval_seconds": state.get("interval_seconds") or cfg.interval_seconds,
            "max_enqueue_per_cycle": state.get("max_enqueue_per_cycle")
            or cfg.max_enqueue_per_cycle,
            "last_cycle": state.get("last_cycle") or {},
            "observed_at": utc_now_iso(),
        }

    @application.post("/api/v1/automation/enable")
    def set_enabled(request: EnableRequest) -> dict[str, Any]:
        def _mutate(state: dict[str, Any]) -> None:
            state["enabled"] = bool(request.enabled)
            if request.enabled:
                interval = int(state.get("interval_seconds") or cfg.interval_seconds)
                state["next_run_at"] = (
                    utc_now() + timedelta(seconds=max(60, interval))
                ).isoformat().replace("+00:00", "Z")
            else:
                state["next_run_at"] = None

        store.update(_mutate)
        return status()

    @application.patch("/api/v1/automation/config")
    def patch_config(request: ConfigPatch) -> dict[str, Any]:
        def _mutate(state: dict[str, Any]) -> None:
            if request.interval_seconds is not None:
                state["interval_seconds"] = int(request.interval_seconds)
            if request.max_enqueue_per_cycle is not None:
                state["max_enqueue_per_cycle"] = int(request.max_enqueue_per_cycle)

        store.update(_mutate)
        # Keep Settings object used by cycles in sync via store values:
        # run_cycle reads max from settings — update cfg via mutable copy on each run.
        if request.interval_seconds is not None:
            object.__setattr__(cfg, "interval_seconds", int(request.interval_seconds))
        if request.max_enqueue_per_cycle is not None:
            object.__setattr__(
                cfg, "max_enqueue_per_cycle", int(request.max_enqueue_per_cycle)
            )
        return status()

    @application.post("/api/v1/automation/run-now")
    async def run_now() -> dict[str, Any]:
        # Use persisted max/interval overrides.
        live = store.load()
        object.__setattr__(
            cfg,
            "max_enqueue_per_cycle",
            int(live.get("max_enqueue_per_cycle") or cfg.max_enqueue_per_cycle),
        )
        object.__setattr__(
            cfg,
            "interval_seconds",
            int(live.get("interval_seconds") or cfg.interval_seconds),
        )
        result = await asyncio.to_thread(
            run_cycle,
            settings=cfg,
            store=store,
            core=core,
            hh=hh,
            scoring=scoring,
            trigger="run_now",
        )
        if result.get("status") == "skipped_already_running":
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "already_running",
                    "message": "Automation cycle already running",
                    "status": "skipped_already_running",
                },
            )
        return result

    return application


def get_app() -> FastAPI:
    return create_app()
