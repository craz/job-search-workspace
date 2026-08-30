# Состояние проекта Job Search Multirepo

**Дата снимка:** 2026-08-31 (UTC+3)  
**Workspace HEAD:** R2.3.3 READY FOR OWNER ACCEPTANCE (local, not pushed)  
**Migration head:** `20260828_15` (single)  
**Ветка:** `main`

## Краткий вердикт

| Область | Статус |
|---|---|
| **R2** | **R2.1–R2.2.A COMPLETE · PUSHED**; **R2.3.1–R2.3.2 COMPLETE** (local); **R2.3.3 READY FOR OWNER ACCEPTANCE**; R2.3.4+ **NOT STARTED** |

Evidence: [`docs/evidence/R2_2_A_INTEGRATED_ACCEPTANCE.md`](docs/evidence/R2_2_A_INTEGRATED_ACCEPTANCE.md), [`docs/SCORING_SERVICE.md`](docs/SCORING_SERVICE.md).

## Решение по «го» / blockers

- **R2.3.3** — review / ACCEPT generation backend slice.
- **R2.3.4** — **не** начинать до ACCEPT R2.3.3.
- **R2.3.4 E2E** требует явного выбора/провижининга production scoring model
  (`job-search-scorer-summary:latest` сейчас отсутствует локально → fail-closed).
- **R2.4** mass scoring — **не** начинать до R2.3.6 calibration evidence.

## Локальные SHA (не pushed)

| Repo | SHA |
|---|---|
| Core | `6f85f30` (R2.3.2) |
| Scoring | `6b4ccc2` (R2.3.3) |
| Workspace | `e8fa6d8` |
