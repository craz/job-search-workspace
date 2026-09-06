"""Runtime configuration for the vacancy automation service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return int(raw)


@dataclass(frozen=True)
class Settings:
    """Compose/env settings for the automation daemon."""

    core_base_url: str
    hh_base_url: str
    scoring_base_url: str
    state_dir: Path
    http_port: int
    interval_seconds: int
    max_enqueue_per_cycle: int
    lock_ttl_seconds: int
    auto_score_max_age_days: int
    default_enabled: bool
    suitable_max_pages: int
    http_timeout_seconds: float

    @property
    def state_path(self) -> Path:
        return self.state_dir / "automation_state.json"


def load_settings() -> Settings:
    """Load settings from environment with safe local defaults."""
    return Settings(
        core_base_url=os.environ.get("CORE_API_URL", "http://127.0.0.1:8000").rstrip("/"),
        hh_base_url=os.environ.get("HH_API_URL", "http://127.0.0.1:8092").rstrip("/"),
        scoring_base_url=os.environ.get("SCORING_API_URL", "http://127.0.0.1:8090").rstrip(
            "/"
        ),
        state_dir=Path(
            os.environ.get("AUTOMATION_STATE_DIR", "/var/lib/job-search-automation")
        ),
        http_port=_env_int("AUTOMATION_HTTP_PORT", 8095),
        interval_seconds=max(60, _env_int("AUTOMATION_INTERVAL_SECONDS", 3600)),
        max_enqueue_per_cycle=max(1, _env_int("AUTO_SCORING_MAX_PER_CYCLE", 20)),
        lock_ttl_seconds=max(300, _env_int("AUTOMATION_LOCK_TTL_SECONDS", 7200)),
        auto_score_max_age_days=max(0, _env_int("AUTO_SCORE_MAX_AGE_DAYS", 14)),
        # Default DISABLED so migration does not start LLM spend.
        default_enabled=_env_bool("AUTOMATION_ENABLED", False),
        suitable_max_pages=max(1, min(20, _env_int("AUTOMATION_SUITABLE_MAX_PAGES", 1))),
        http_timeout_seconds=float(os.environ.get("AUTOMATION_HTTP_TIMEOUT_SECONDS", "600")),
    )
