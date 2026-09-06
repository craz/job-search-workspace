"""Freshness gate aligned with Scoring PB-02A / r241b-v1 (no LLM)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

FRESHNESS_POLICY_VERSION = "r241b-v1"
AUTO_SCORE_MAX_AGE_DAYS = 14

FreshnessStatus = Literal["fresh", "expired_by_freshness", "cannot_determine"]


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def evaluate_freshness(
    vacancy: dict[str, Any],
    *,
    now: datetime | None = None,
    max_age_days: int = AUTO_SCORE_MAX_AGE_DAYS,
) -> FreshnessStatus:
    """Mirror Scoring evaluate_freshness status only (policy must stay aligned)."""
    clock = now.astimezone(UTC) if now is not None else datetime.now(UTC)
    published = _parse_timestamp(vacancy.get("source_published_at"))
    if published is not None:
        anchor = published
    else:
        first_seen = _parse_timestamp(vacancy.get("first_seen_at"))
        if first_seen is None:
            return "cannot_determine"
        anchor = first_seen
    age_days = (clock - anchor).total_seconds() / 86400.0
    if age_days <= float(max_age_days):
        return "fresh"
    return "expired_by_freshness"
