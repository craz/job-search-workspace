# Состояние проекта Job Search Multirepo

**Дата снимка:** 2026-08-31 (UTC+3)  
**Workspace HEAD:** R2.3.4 READY FOR OWNER ACCEPTANCE (local, not pushed)  
**Migration head:** `20260828_15` (single)  
**Ветка:** `main`

## Краткий вердикт

| Область | Статус |
|---|---|
| **R2** | **R2.1–R2.2.A COMPLETE · PUSHED**; **R2.3.1–R2.3.3 COMPLETE** (local); **R2.3.4 READY FOR OWNER ACCEPTANCE**; R2.3.5+ **NOT STARTED** |

Evidence: [`docs/evidence/R2_2_A_INTEGRATED_ACCEPTANCE.md`](docs/evidence/R2_2_A_INTEGRATED_ACCEPTANCE.md), [`docs/SCORING_SERVICE.md`](docs/SCORING_SERVICE.md).

## Решение по «го» / blockers

- **R2.3.4** — owner review / ACCEPT первого реального FAST scoring E2E.
- **R2.3.5** — reuse/staleness/hardening — **не** начинать до ACCEPT R2.3.4.
- **R2.3.6** — calibration — planned; **не** начинать implementation.
- **R2.4** mass scoring — **не** начинать до R2.3.6 calibration evidence.

## Локальные SHA (не pushed)

| Repo | SHA | Notes |
|---|---|---|
| Core | `6f85f30` + R2.3.4 AssessmentDetail | pending commit |
| Scoring | `fa2afa0` + R2.3.4 | pending commit |
| Workspace | `62b3401` + docs | pending commit |

## R2.3.4 live evidence (technical)

- Vacancy `b12a42c5-4f50-477c-b173-a355e3161f5d` («Руководитель проектов (ИТ)»)
- Assessment `85eee55e-7291-447d-808e-e5e0e2aee0e4` · score **92** · verdict **apply**
- Provisional model `job-search-scorer-summary:latest` (base `qwen3.5:9b-q4_K_M`)
- Scoring HTTP `127.0.0.1:8090` · Core `127.0.0.1:18000` · Web 200
