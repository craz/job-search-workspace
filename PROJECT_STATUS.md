# Состояние проекта Job Search Multirepo

**Дата снимка:** 2026-08-31 (UTC+3)  
**Workspace HEAD:** R2.3.6.1 owner labeling UI READY (local, not pushed)  
**Migration head:** `20260828_15` (single)  
**Ветка:** `main`

## Краткий вердикт

| Область | Статус |
|---|---|
| **R2** | **R2.1–R2.3.5 COMPLETE** (local); **R2.3.6 IN PROGRESS**; **R2.3.6.1 READY FOR OWNER LABELING (Web UI)** |

## Решение по «го» / blockers

- **R2.3.6.1** — owner blind labeling 30 real cases via Web UI
  (`/calibration?suite_id=cal-r2361-realhh-20260831`).
- **R2.3.6.2** — benchmark execution — **не** начинать до завершения owner labels.
- **R2.4** mass scoring — **не** начинать до R2.3.6 calibration evidence + owner decision.

## Локальные SHA (не pushed)

| Repo | SHA | Notes |
|---|---|---|
| Core | `6560463` | resume_suitable vacancy list provenance |
| Scoring | pending labeling HTTP | calibration store + labeling API |
| Web | pending labeling UI | `/calibration` blind UI |
| Workspace | pending | docs + gitlinks + compose |

## R2.3.6.1 highlights

- Private suite: `cal-r2361-realhh-20260831` · 30 verified real HH cases · seed `20260831`
- Prior suite `cal-20260831-20260831` **invalidated** (contaminated pool)
- Labels: **0/30** (awaiting owner)
- Owner UX: Web `/calibration` (CLI remains technical fallback)
- Storage: `{SCORING_STATE_DIR}/calibration/` (gitignored)
- No Core Assessment writes; no Ollama benchmark runs yet

## R2.3.5 (retained)

- Derived current/stale, single-flight, failure diagnostics — **COMPLETE**
