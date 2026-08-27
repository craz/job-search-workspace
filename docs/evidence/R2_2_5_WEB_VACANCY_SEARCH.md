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

## Gates

| Repo | Result |
|---|---|
| Core | unit 55 · integration 27 · contract 9 · bdd 18 |
| HH | unit 132 (+1 skip) · contract 16 · bdd 13 |
| Web | unit 5 · integration 36 · contract 6 · bdd 10 |

Migration head: **`20260828_13`**

R2.2.A / R2.3 **NOT STARTED**. **Not pushed.**
