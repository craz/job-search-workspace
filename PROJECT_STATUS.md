# Состояние проекта Job Search Multirepo

**Дата снимка:** 2026-08-27 (UTC+3)  
**Workspace HEAD:** local R2.2 decomposition (ahead of origin after docs commit)  
**Web submodule HEAD:** `9abe407` (== origin/main; R2.1.5)  
**HH submodule HEAD:** `737ac9d` (== origin/main)  
**Core submodule HEAD:** `aa81914` (== origin/main)  
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
| **R2** | **R2.1 COMPLETE · OWNER ACCEPTED · PUSHED**; **R2.2 DECOMPOSITION READY FOR OWNER ACCEPTANCE**; production R2.2 **NOT STARTED**; R2.3+ **NOT STARTED** |
| Content / Telegram §8 | не начат |
| **PB-DATA-00** | **COMPLETE — Gate CLOSED** |
| **R0** | **CLOSED — Gate R0 ACCEPTED WITH NON-BLOCKING DEBT** |

R2.1 evidence: [`docs/R2_1A_INTEGRATED_EVIDENCE.md`](docs/R2_1A_INTEGRATED_EVIDENCE.md) (`5df713c` pushed).  
R2.2 decomposition: [`docs/R2_2_DECOMPOSITION.md`](docs/R2_2_DECOMPOSITION.md).

## Решение по «го» / blockers

- R2.1 closed and pushed.
- **«Го»** = `ACCEPT` декомпозиции R2.2 (или замечания).
- Model boundaries: SearchProfile = criteria only; execution → SearchRun
  `execution_snapshot`; per-vacancy **SearchRunItem**; list-first + detail when
  needed for scoring-ready content.
- Live `GET /vacancies` → **403**; browser vacancy search не авто-разрешён.
- Production R2.2 / R2.3 — **не** начинать до OWNER ACCEPTED декомпозиции.
