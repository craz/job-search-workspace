# Состояние проекта Job Search Multirepo

**Дата снимка:** 2026-08-31 (UTC+3)  
**Workspace HEAD:** R2.3.6.1 READY FOR OWNER LABELING (local, not pushed)  
**Migration head:** `20260828_15` (single)  
**Ветка:** `main`

## Краткий вердикт

| Область | Статус |
|---|---|
| **R2** | **R2.1–R2.3.5 COMPLETE** (local); **R2.3.6 IN PROGRESS**; **R2.3.6.1 READY FOR OWNER LABELING** |

## Решение по «го» / blockers

- **R2.3.6.1** — owner blind labeling 30 real cases (`cal-20260831-20260831`).
- **R2.3.6.2** — benchmark execution — **не** начинать до завершения owner labels.
- **R2.4** mass scoring — **не** начинать до R2.3.6 calibration evidence + owner decision.

## Локальные SHA (не pushed)

| Repo | SHA | Notes |
|---|---|---|
| Core | `a76969d` | unchanged |
| Scoring | pending R2.3.6.1 | calibration harness |
| Workspace | pending R2.3.6.1 | docs + gitlink |

## R2.3.6.1 highlights

- Private suite: `cal-20260831-20260831` · 30 real HH cases · seed `20260831`
- Labels: **0/30** (awaiting owner)
- Storage: `{SCORING_STATE_DIR}/calibration/` (gitignored)
- No Core Assessment writes; no Ollama benchmark runs yet

## R2.3.5 (retained)

- Derived current/stale, single-flight, failure diagnostics — **COMPLETE**
