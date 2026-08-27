# Состояние проекта Job Search Multirepo

**Дата снимка:** 2026-08-27 (UTC+3)  
**Workspace HEAD:** local R2.2.2 (ahead of origin after HH gitlink + evidence)  
**Web submodule HEAD:** `9abe407` (== origin/main; R2.1.5)  
**HH submodule HEAD:** local R2.2.2 browser vacancy acquire (not pushed)  
**Core submodule HEAD:** `a12022a` (== origin/main; R2.2.1)  
**Ветка:** `main`

Этот файл — оперативный снимок «где мы сейчас». Детальный план и gate-критерии
живут в [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md); архитектура — в
[`ARCHITECTURE_PLAN.md`](ARCHITECTURE_PLAN.md).

## Краткий вердикт

| Область | Статус |
|---|---|
| Workspace 0A / inventory | готово |
| Core + Web MVP | готово |
| Scoring (host Ollama pipeline) | базово готово; **R2.3 foundation not started** |
| OSINT | в основном готово |
| HH read-path | R1.1–R1.6 **COMPLETE · PUSHED** |
| **R1 / PB-00** | **COMPLETE · Gate R1 CLOSED** (OWNER ACCEPTED 2026-08-27) |
| **R2** | **R2.1 COMPLETE · PUSHED**; **R2.2 DECOMPOSITION OWNER ACCEPTED · PUSHED**; **R2.2.1 COMPLETE · PUSHED**; **R2.2.2 READY FOR OWNER ACCEPTANCE** (browser RO vacancy acquire); R2.2.3 / R2.3 **NOT STARTED** |
| Content / Telegram §8 | не начат |
| **PB-DATA-00** | **COMPLETE — Gate CLOSED** |
| **R0** | **CLOSED — Gate R0 ACCEPTED WITH NON-BLOCKING DEBT** |

R2.2 decomposition: [`docs/R2_2_DECOMPOSITION.md`](docs/R2_2_DECOMPOSITION.md) (`2876c2e` pushed).  
R2.2.1 Core: `a12022a` · workspace tip that closed the slice: `3b6c2a9` (pushed).  
Official API probe: [`docs/evidence/R2_2_2_HH_VACANCY_API_PROBE.md`](docs/evidence/R2_2_2_HH_VACANCY_API_PROBE.md) (pushed `53a2b8b`).  
Browser acquire evidence: [`docs/evidence/R2_2_2_BROWSER_VACANCY_ACQUIRE.md`](docs/evidence/R2_2_2_BROWSER_VACANCY_ACQUIRE.md).

## Решение по «го» / blockers

- **«Го»** = `ACCEPT` R2.2.2 (или замечания).
- R2.2.3 / Core Vacancy upsert — **не** начинать до ACCEPT R2.2.2.
- Official `GET /vacancies` остаётся 403; supported path = **browser RO**.
