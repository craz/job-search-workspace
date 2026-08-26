# Состояние проекта Job Search Multirepo

**Дата снимка:** 2026-08-26 (UTC+3)  
**Workspace HEAD:** local R1.3 COMPLETE · PUSHED (docs tip pending)  
**Web submodule HEAD:** `d3df5f901026b460eb6897bf92a0517328fa24e0`  
**HH submodule HEAD:** `d39ba5a9a246601d2e7dbeb43beac915d922e69b`  
**Ветка:** `main`

Этот файл — оперативный снимок «где мы сейчас». Детальный план и gate-критерии
живут в [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md); архитектура — в
[`ARCHITECTURE_PLAN.md`](ARCHITECTURE_PLAN.md). R0 design:
[`docs/R0_DESIGN.md`](docs/R0_DESIGN.md).

## Краткий вердикт

| Область | Статус |
|---|---|
| Workspace 0A / inventory | готово |
| Core + Web MVP | готово |
| Scoring (host Ollama pipeline) | базово готово |
| OSINT (website / people → Core) | в основном готово |
| HH read-path | vacancies + **`GET /me` (R1.2)** + **browser RO resumes (R1.3)**; documented Docker host-proxy bridge; `/resumes/mine` **403**; R1.1–R1.3 **COMPLETE** |
| HH write-path (API) | код dual-gate готов; **production API apply заблокирован scope HH-приложения** |
| **R1 / PB-00** | R1.1–R1.3 **COMPLETE · PUSHED**; R1.4–R1.6 not started; **Gate R1 OPEN** |
| Content / Telegram §8 | не начат (submodule stub) |
| Сквозная сборка §9 / Hermes §10 | не закрыты |
| **Plan revisions** | **ARCHITECTURE_PLAN rev. 2** · **IMPLEMENTATION_PLAN rev. 2** |
| **PB-DATA-00** | **COMPLETE — Gate CLOSED** (one-time owner bootstrap isolated) |
| **R0 / PB-UX-00 Web redesign** | **CLOSED — Gate R0 ACCEPTED WITH NON-BLOCKING DEBT (2026-08-22)** |

**Gate R0:** **ACCEPTED WITH NON-BLOCKING DEBT** (product owner, 2026-08-22).  
**PB-UX-00:** **CLOSED** (T-UX-00.1 … T-UX-00.9 complete).  
**Gate PB-DATA-00:** **CLOSED** (DATA-00.1–00.7).  
**R0** больше не является текущей реализационной работой.

**Главный продуктовый next:** **R1.4** (active resume select).  
Host-proxy: [`docs/runbooks/hh-docker-host-proxy.md`](docs/runbooks/hh-docker-host-proxy.md).  
R1.2–R1.3: OWNER ACCEPTED / COMPLETE · PUSHED (2026-08-26).  
Full R1: connection → profile → resume list → active resume → linkage → recovery → Gate R1.

Артефакты R0:
- [`DESIGN.md`](DESIGN.md) — normative visual system (Calm Dense Productivity, dark primary)
- [`docs/R0_ACCEPTANCE.md`](docs/R0_ACCEPTANCE.md) — Gate R0 acceptance record
- [`docs/R0_DESIGN.md`](docs/R0_DESIGN.md) — PB-UX-00 closed
- Screenshots: `docs/r0/screenshots/t-ux-00.8-ia5/`
- Web: `services/web/.../static/` @ `86f37cb`

Content/Telegram, browser HH apply и Scoring foundation **не являются immediate next** — см. Roadmap R1+.

## Gate R0 — accepted state (2026-08-22)

- Calm Dense Productivity; primary R0 scheme: **dark**
- **5 top-level workspaces:** Vacancies, Journal, Metrics, People, Hypotheses
- Assessment / ScoringResult — **contextual to Vacancy**, not standalone workspace
- Web tests: **37 passed** @ Web `86f37cb`
- Gate has **no blockers**

**Known non-blocking debt** (не reopen R0 без architecture blocker):
- ~~workspace cursor-rule test involving `12-no-choice-menus.mdc`~~ — **RESOLVED** (single global `alwaysApply`: `00-project-context.mdc`);
- legacy naming (`panel-eyebrow`, metrics class naming);
- duplicate smoke/demo Core data;
- repository housekeeping / old untracked R0 artifacts (`t-ux-00.8-final/`, `review2/`, prompts).

## По этапам плана

### 0–2. Workspace, inventory, каркасы

- Multirepo + submodules + bootstrap/doctor — работают.
- Исторический code inventory монолита зафиксирован в `docs/inventory/*`.
- Продуктовые реpositories существуют; эталон качества — Core.

### 3. Core

- PostgreSQL/Alembic, Company/Vacancy/Application/metrics/people/hypotheses/assessments — публичный HTTP/JSON API.
- Consumers ходят только через контракты, без shared DB.

### 4. Web

- HTTP-only Core consumer; OSINT research view; R0 IA и visual system приняты Gate R0.

### 5. HH — подробно

**Read-ready:** `services/hh/docs/runbooks/hh-read-gate.md`.

**Production API apply blocker:** `GET /negotiations`, `GET /resumes/mine` → **403**
для текущего HH-приложения; browser apply transport не реализован.

### 6. Scoring

- JSON queue, host Ollama, Assessment → Core — базовый pipeline есть; R2 redesign deferred.

### 7. OSINT

- Website / mirrors / people research / confirm → Core; manual/on-demand triggers.

### 8–11. Ещё впереди

- §8 Content + Telegram — stub submodule, не в compose.
- §9 Compose E2E / backup / doctor расширения.
- §10 Hermes compatibility — отложен.

## Локальный runtime (ориентир)

| Сервис | Порт / заметка |
|---|---|
| Core | `127.0.0.1:18000` |
| Web | `127.0.0.1:18080` |
| HH noVNC | `127.0.0.1:6080` |
| HH OAuth publish | `127.0.0.1:8767` |
| Host Ollama | `127.0.0.1:11434` |

Не коммитить: `services/hh/.env`, `services/hh/.local/**`, токены, cookies, profile.

## Решение по «го» / blockers

- **«Го»** = старт **R1.4** (active resume select + persistence per US-00.4/00.5).  
  Gate R1 остаётся OPEN до R1.4–R1.6 + R1.A.

## Как обновлять этот файл

После каждого завершённого зелёного среза (или явного запроса «обнови статус»):

1. Обновить дату и HEAD SHA.
2. Поправить таблицу вердикта и блок HH/блокеров по факту.
3. Держать «Главный продуктовый next» согласованным с Roadmap и `ARCHITECTURE_PLAN.md`.
