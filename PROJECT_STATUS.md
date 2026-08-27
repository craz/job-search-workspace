# Состояние проекта Job Search Multirepo

**Дата снимка:** 2026-08-27 (UTC+3)  
**Workspace HEAD:** local docs (R2.1 decomposition accepted; push pending)  
**Web submodule HEAD:** `7bc0bd5`  
**HH submodule HEAD:** `5163196`  
**Core submodule HEAD:** `053e7d9`  
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
| **R2** | **planning active**; R2.1 DECOMPOSITION **OWNER ACCEPTED**; production **NOT STARTED** |
| Content / Telegram §8 | не начат |
| **PB-DATA-00** | **COMPLETE — Gate CLOSED** |
| **R0** | **CLOSED — Gate R0 ACCEPTED WITH NON-BLOCKING DEBT** |

**Главный продуктовый next:** после docs ACCEPT — **R2.1.1** (Core ResumeVersion storage).  
R2.1.1 / R2.2+ / production implementation: **NOT STARTED**.

Decomposition: [`docs/R2_PB01_DECOMPOSITION.md`](docs/R2_PB01_DECOMPOSITION.md).

## Решение по «го» / blockers

- **«Го»** = старт только **R2.1.1** (Core immutable ResumeVersion), после
  owner acceptance этого docs-only шага.
- Или если скажешь **push** — сначала push docs commit.
- R2.2+ / Scoring foundation / vacancy ingestion — **не** стартовать из «го».
