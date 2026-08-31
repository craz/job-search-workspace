# Состояние проекта Job Search Multirepo

**Дата снимка:** 2026-08-31 (UTC+3)  
**Workspace HEAD:** R2.3.5 READY FOR OWNER ACCEPTANCE (local, not pushed)  
**Migration head:** `20260828_15` (single)  
**Ветка:** `main`

## Краткий вердикт

| Область | Статус |
|---|---|
| **R2** | **R2.1–R2.2.A COMPLETE · PUSHED**; **R2.3.1–R2.3.4 COMPLETE** (local); **R2.3.5 READY FOR OWNER ACCEPTANCE**; R2.3.6+ **PLANNED** |

Evidence: [`docs/evidence/R2_2_A_INTEGRATED_ACCEPTANCE.md`](docs/evidence/R2_2_A_INTEGRATED_ACCEPTANCE.md), [`docs/SCORING_SERVICE.md`](docs/SCORING_SERVICE.md).

## Решение по «го» / blockers

- **R2.3.5** — owner review / ACCEPT reuse, staleness, single-flight, failure diagnostics.
- **R2.3.6** — calibration — planned; **не** начинать implementation.
- **R2.4** mass scoring — **не** начинать до R2.3.6 calibration evidence.

## Локальные SHA (не pushed)

| Repo | SHA | Notes |
|---|---|---|
| Core | pending R2.3.5 identity filter | `scoring_identity_hash` query param |
| Scoring | pending R2.3.5 | state resolver, single-flight, diagnostics |
| Workspace | pending R2.3.5 | docs + gitlinks |

## R2.3.5 highlights (technical)

- Derived `never_scored` \| `current` \| `stale` — no `is_current` DB column
- `GET /api/v1/vacancies/{id}/scoring-state` + CLI `resolve-state`
- Exact Core lookup: `GET /api/v1/assessments?scoring_identity_hash=…`
- In-process single-flight keyed by identity; cross-process not guaranteed
- Bounded failure diagnostics under `{state_dir}/failures/` (TTL, max files/size)
- JobStore non-durable; Core Assessment reuse survives restart

## R2.3.4 live evidence (retained)

- Vacancy `b12a42c5-4f50-477c-b173-a355e3161f5d` («Руководитель проектов (ИТ)»)
- Assessment `85eee55e-7291-447d-808e-e5e0e2aee0e4` · score **92** · verdict **apply**
- Identity `d483e06ec26f5286f871a2f268d8c5ca77a8ac23a15cee8279f00d6846fd8cf1`
- Provisional model `job-search-scorer-summary:latest` (base `qwen3.5:9b-q4_K_M`)
- Scoring HTTP `127.0.0.1:8090` · Core `127.0.0.1:18000` · Web 200
