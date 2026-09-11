# SUITABLE FRESHNESS-FIRST UX — evidence

**When (UTC):** 2026-09-11T06:42–06:50Z  
**When (MSK):** 2026-09-11 09:42–09:50 MSK  
**push=0**  
**Ports:** Web 18080 · Core 18000

## Why the previous default was slow (250-item / max_pages=5)

Recent successful 250-run before the change:

| Field | Value |
|---|---|
| run_id | `8ef61637-4efe-4951-88ee-4a564d45505f` |
| started (UTC) | 2026-09-11T05:44:43Z (08:44 MSK) |
| finished (UTC) | 2026-09-11T05:50:34Z (08:50 MSK) |
| duration | **350.8 s (~5.8 min)** |
| execution | `max_pages=5`, `start_page=0`, `order=publication_time` |
| SERP checked | 250 |
| created / unchanged / errors | 97 / 153 / 0 |
| source_total | 2827 |
| progress | pages_fetched=5; **no** `detail_planned`/`detail_fetched` (Core schema `extra=forbid` dropped them) |

Slow because: 5 SERP pages × detail fetches for every NEW id (97 cards) on Playwright, sequential. Create-only already skipped 153 known ids, but page budget 5 still forced deep backfill on every default click.

## Default before → after

| | Before | After |
|---|---|---|
| `SUITABLE_MAX_PAGES_PER_RUN` | 5 (~250) | **1 (~50 newest)** |
| Hint | «до 5 страниц HH (~250…)» | «свежие сначала: 1 страница HH (~50 новейших)» |
| «Проверить подходящие» | start_page=0, max_pages=5 | start_page=0, **max_pages=1** |
| «Загрузить ещё» | next_page, max_pages=5 | next_page, **max_pages=1** (explicit deeper backfill) |
| order | publication_time | publication_time (unchanged; no second «Новые» flow) |
| lookup / create-only | SERP → bulk lookup → details NEW only | unchanged |

## Live create-only progress (API)

Run `49d9344c-9879-4fdd-b511-bc255a9692ad` (`max_pages=1`, start_page=0):

- duration **37.8 s** (vs 350.8 s for 250)
- partition: serp_checked=50 · already_in_db=40 · new_ids=10 · hh_cards_fetched=10 · created=10
- mid-run progress samples (`live_api_progress.json`):  
  `checked=50, unchanged=40, detail_planned=10, detail_fetched=0→9` every card

Core now allowlists `detail_planned` / `detail_fetched` / CAPTCHA URL fields so HH progress patches no longer 422.

## Continuation

`continuation_start_page_1.json`: `start_page=1`, `max_pages=1` → page_from/to=1, next_page=2, more_remaining=true, serp 50 / already_in_db 50 / hh_cards 0 (create-only). Not a restart of page 0.

## Browser evidence

| File | What |
|---|---|
| `01_hint_default.png` | Freshness-first Russian hint + «Проверить подходящие» |
| `02_live_counters.png` | Live line: «Проверено SERP 50 · Уже в базе 40 · Новых 10 · Карточек HH загружено 4 из 10» |
| `03_terminal_load_more.png` | Terminal + «можно загрузить ещё» + «Загрузить ещё» visible |
| `04_real_click_live.png` | Real click showed create-only «Проверено SERP …» (note: page-load `resumes-list` can race ProfileLock) |

## Tests

- web: contract suitable + js-syntax + js-smoke PASS
- core: `tests/unit/test_search_runs.py` PASS (detail_* progress)
- hh: orchestration + suitable pagination unit PASS

## Commits

See completion report (local only, push=0).
