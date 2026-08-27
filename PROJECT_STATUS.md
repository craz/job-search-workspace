# Состояние проекта Job Search Multirepo

**Дата снимка:** 2026-08-27 (UTC+3)  
**Workspace HEAD:** local R2.1.3 (ahead of origin)  
**Web submodule HEAD:** `7bc0bd5`  
**HH submodule HEAD:** `f54ecfb` (ahead of origin; R2.1.3)  
**Core submodule HEAD:** `5f8039c` (ahead of origin; docs only)  
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
| **R2** | R2.1 DECOMPOSITION **OWNER ACCEPTED**; **R2.1.1–R2.1.2 COMPLETE · PUSHED**; **R2.1.3 READY FOR OWNER ACCEPTANCE**; R2.1.4+ **NOT STARTED** |
| Content / Telegram §8 | не начат |
| **PB-DATA-00** | **COMPLETE — Gate CLOSED** |
| **R0** | **CLOSED — Gate R0 ACCEPTED WITH NON-BLOCKING DEBT** |

Decomposition: [`docs/R2_PB01_DECOMPOSITION.md`](docs/R2_PB01_DECOMPOSITION.md).

## Решение по «го» / blockers

- **«Го»** после ACCEPT R2.1.3 = старт только **R2.1.4** (version/dedup behaviour product slice).
- Или если скажешь **push** — push HH + workspace R2.1.3 baseline.
- R2.1.4 / Web UX / Scoring — **не** до ACCEPT R2.1.3.
