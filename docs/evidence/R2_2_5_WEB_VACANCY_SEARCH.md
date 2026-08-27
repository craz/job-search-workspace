# R2.2.5 — Primary resume-suitable Web flow (correction + temporal)

**Date:** 2026-08-28  
**Status:** READY FOR OWNER ACCEPTANCE (local; **not** pushed)

## Temporal model (R2.2.5 correction)

| Field | Semantics |
|---|---|
| `first_seen_at` | First successful Job Search ingest of `(source, external_id)`; immutable |
| `last_seen_at` | Latest successful fetch/ingest; advances on created/updated/**unchanged** |
| `source_published_at` | Nullable; populated only when HH supplies reliable datetime (currently NULL) |

Legacy equivalent: JSONL `captured_at` / scoring column **«Когда»** — local acquisition freshness, not HH `published_at`.

**Migration `20260828_13` backfill (approximate):**

- `first_seen_at = created_at`
- `last_seen_at = COALESCE(updated_at, created_at)`

Pre-migration rows: `first_seen_at` does **not** prove original HH fetch time.

**Default list order:** `first_seen_at DESC` (not `last_seen_at DESC` — recheck must not float old vacancies above newly discovered).

**content_hash:** excludes `first_seen_at` / `last_seen_at`; `source_published_at` in hash only when supplied as source-owned data.

## Live Web URL

http://127.0.0.1:18080/#vacancies

## Primary acquisition (unchanged)

`POST /api/v1/hh/vacancies/suitable` · `order_by=publication_time` · `max_pages=1`

## Live temporal evidence (2026-08-28)

| Check | Result |
|---|---|
| A backfill | existing rows: `first_seen_at≈created_at`, `source_published_at=null` |
| API order | `first_seen_at DESC` confirmed |
| Repeat run | unchanged=50; `last_seen_at` advanced without rank jump |
| Order invariant | vacancy with newer `last_seen_at` but older `first_seen_at` stays below newer-first-seen row |
| Web | «Получена» present; no «Опубликовано» when `source_published_at` null |

Example after repeat: rank-0 `first_seen=20:44:14`; rechecked row `first_seen=20:14:57`, `last_seen=21:38:46`, rank=4.

## OSINT / mirrors visibility (not a regression)

Web `vacancyRow()` shows collapsible **«OSINT и зеркала»** only when:

```text
item.company.website_url  OR  existing evidenceCount > 0
```

Workflow status (`new` vs `reviewing`) is **not** a gate.

Live example:

| Vacancy | status | `company.website_url` | OSINT section |
|---|---|---|---|
| Synthetic Integration Engineer | reviewing | `https://workspace-smoke.example/` | visible |
| Product Manager (HH ingest) | new | `null` | hidden |

New HH-ingested vacancies remain structurally OSINT-compatible (UUID, company FK, source/external_id); OSINT POST uses the same contract once `website_url` is set. Full website discovery is R3 scope.

## HH egress misconfiguration guard (R2.2.5)

Root cause of false «сеть или временный сбой» on resume list: `HTTP_PROXY=http://127.0.0.1:2080` inside `hh` container (loopback ≠ host proxy).

**Fix:** canonical `make up` applies `hh-egress` override → `http://hh-egress:3128`.

**Hardening:** `browser_proxy_unavailable` / recovery `local_egress_unavailable`; `/health/ready` exposes `egress.proxy_url` and fails when loopback proxy is configured.

## Gates

| Repo | Result |
|---|---|
| Core | unit 55 · integration 27 · contract 9 · bdd 18 |
| HH | unit 140 (+1 skip) · contract 16 · bdd 13 |
| Web | unit 5 · integration 36 · contract 11 · bdd 10 |

## Owner UI feedback (final small correction)

| Item | Change |
|---|---|
| «Получена» | `DD.MM.YYYY, HH:MM` via `formatFirstSeen()` — year always shown |
| Hierarchy | Vacancy title stronger; company/description secondary; meta `#b4bcc8`; subtle row hover |
| Workflow badges | `new→accent`, `reviewing→info`, `shortlisted→success`, `rejected→danger`; source `hh` stays `neutral` |
| Scoring | No score/verdict styling (reserved for R2.4) |

Migration head: **`20260828_13`**

R2.2.A / R2.3 **NOT STARTED**. **Not pushed.**
