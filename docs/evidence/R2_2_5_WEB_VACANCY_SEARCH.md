# R2.2.5 — Primary resume-suitable Web flow (correction)

**Date:** 2026-08-27  
**Status:** READY FOR OWNER ACCEPTANCE (local; **not** pushed)  
**Research:** [`R2_2_5_PRIMARY_FLOW_RESEARCH.md`](R2_2_5_PRIMARY_FLOW_RESEARCH.md) — OWNER ACCEPTED

## Live Web URL

http://127.0.0.1:18080/#vacancies

## Freshness / order proof (reconfirmed live)

| Order | `order_by` | Top-8 vs other |
|---|---|---|
| relevance (default) | `relevance` | — |
| publication_time | `publication_time` | **0 overlap** with relevance top-8 |

Heading both times: «Найдено 2 272 подходящих вакансии для резюме».  
Primary default: **`publication_time`**.

## Live primary runs (via Web `POST /api/v1/hh/vacancies/suitable`)

| Run | HTTP | status | source_total | found (processed) | created | updated | unchanged | profile_id | acquisition_kind |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 200 (~70s) | success | **2272** | 20 | 20 | 0 | 0 | **null** | **resume_suitable** |
| 2 (repeat) | 200 (~153s) | success | **2272** | 50 | 29 | 0 | 21 | **null** | **resume_suitable** |

Notes:

- `observed_page_size` varies (20 then 50); UI says «до ~50».
- Repeat does **not** duplicate Core Vacancy rows (`(source, external_id)`).
- Vacancy totals: 469 → 489 → 518 (+20, then +29).
- SERP guard: `ok=true`, `source_total=2272`.
- `candidate_context_snapshot`: active resume id + title + optional version ids.
- `criteria_snapshot`: `{}`.
- `execution_snapshot.order`: `publication_time`, `max_pages=1`.

## Product surfaces

- Primary: «Подходящие вакансии» + «Проверить подходящие» (no criteria form).
- Secondary: «Свой поиск» deferred (no silent auto-import).
- Local «Фильтр списка»: client-side only on loaded Core list.
- No «Только с зарплатой» on primary.

## Gates (TECHNICAL PASS)

| Repo | Result |
|---|---|
| Core | unit 50 · integration 27 · contract 9 · bdd 18 |
| HH | unit 132 (+1 skip) · contract 16 · bdd 13 |
| Web | unit 5 · integration 36 · contract 6 · bdd 10 |

Migration head: **`20260827_12`**.

## Non-scope

R2.2.A / R2.3 **NOT STARTED**. **Not pushed.**
