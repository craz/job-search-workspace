# Состояние проекта Job Search Multirepo

**Дата снимка:** 2026-08-22 (UTC+3)  
**Workspace HEAD:** `5afbcd6` (docs update for T-UX-00.8 pending commit)  
**Web submodule HEAD:** `b65522d`  
**HH submodule HEAD:** `1ec60bf`  
**Ветка:** `main` (workspace ahead of origin; push только по явному запросу)

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
| HH read-path | **read-ready** |
| HH write-path (API) | код dual-gate готов; **production API apply заблокирован scope HH-приложения** |
| Content / Telegram §8 | не начат |
| Сквозная сборка §9 / Hermes §10 | не закрыты |
| R0 / PB-UX-00 Web redesign | **T-UX-00.8 complete (incl. IA correction) → Gate R0 pending** |

**Главный продуктовый next:** **T-UX-00.9** — Gate R0 with product owner.  
**Текущий task:** T-UX-00.8 complete — regression, visual review, **IA correction** (Assessments removed from top-level nav; contextual in Vacancy). Gate R0 **не закрыт** агентом.

Артефакты направления:
- [`DESIGN.md`](DESIGN.md) — normative visual system
- [`docs/R0_ACCEPTANCE.md`](docs/R0_ACCEPTANCE.md) — T-UX-00.8 acceptance (**READY FOR GATE R0**; five-section IA)
- [`docs/R0_DESIGN_REFERENCES.md`](docs/R0_DESIGN_REFERENCES.md) — сравнение референсов  
- [`docs/R0_UI_AUDIT.md`](docs/R0_UI_AUDIT.md) — audit  
- Screenshots: `docs/r0/screenshots/t-ux-00.6-dark/`, `t-ux-00.7/`, `t-ux-00.8-ia5/`
- Web: `services/web/src/job_search_web/static/{index.html,styles.css,app.js}` @ `b65522d` (+ IA5 uncommitted)

Content/Telegram, browser HH apply, Scoring redesign и дальнейшее service-driven
развитие по старой очереди `IMPLEMENTATION_PLAN.md` **сейчас не являются next
step**.
## По этапам плана

### 0–2. Workspace, inventory, каркасы

- Multirepo + submodules + bootstrap/doctor — работают.
- Inventory исходного `/data/Projects/job_search` зафиксирован.
- Продуктовые репозитории существуют; эталон качества — Core.

### 3. Core

- PostgreSQL/Alembic, Company/Vacancy/Application/metrics/people — в работе как
  публичный HTTP/JSON API.
- Consumers ходят только через контракты, без shared DB.

### 4. Web

- HTTP-only Core consumer, UI подтверждений OSINT/people — готово как MVP.

### 5. HH — подробно

**Read-ready (подтверждено recreate-gate):**  
`docs` → `services/hh/docs/runbooks/hh-read-gate.md`.

Сделано:

1. Chromium / Playwright / noVNC в HH image; Compose loopback noVNC `127.0.0.1:6080`.
2. Volumes `hh-state` / `hh-profile` + profile lock.
3. Operator login: `auth open-login` / `confirm` / `clear`; `login_ready`.
4. Vacancies sync (public API или fixture) → Core.
5. Applications/metrics: fixture + live GET `/negotiations`; metrics +=
   `/resumes/mine` (403 → fallback).
6. OAuth: `oauth-url` / `exchange-code` / `set-token` / `token-status` /
   `oauth-acquire` (loopback; default publish `127.0.0.1:8767`, зарегистрированный
   в архиве redirect — `http://127.0.0.1:8765/callback`).
7. Dry-run apply без HH write.
8. Limited apply: dual-gate
   (`JOB_SEARCH_HH_EXTERNAL_WRITES_ENABLED` + `--i-authorize-hh-writes`) +
   `login_ready`/token → `HttpApplyTransport` POST `/negotiations`;
   captcha/403/429 → `stopped_captcha`. Compose default: writes **off**.

Runtime / секреты (без значений в git):

- Приватный `services/hh/.env` импортирован из архива `job_search/.env`
  (client id/secret, UA email, redirect, proxy).
- Токен обновлён с хоста через proxy `127.0.0.1:2080`; в контейнере proxy
  должен идти на `host.docker.internal:2080` (`extra_hosts` в Compose).
- Compose: `env_file: ./services/hh/.env`.

Блокер production API apply (факт проверки 2026-08-21):

- `GET /me` → 200 (applicant token живой).
- `GET /negotiations`, `GET /resumes/mine` → **403 forbidden** для текущего
  HH-приложения (не хватает applicant API scope).
- В архиве отклики/просмотры шли через browser scrape именно поэтому.
- Значит dual-gated API POST тоже упрётся в scope, пока приложение не расширят
  на dev.hh.ru **или** не появится browser apply transport.

### 6. Scoring

- Очередь, host Ollama, Assessment → Core, model CLI — базовый pipeline есть.

### 7. OSINT

- Website / mirrors / people research / confirm → Core — сделано; provenance
  confidence — частично.

### 8–11. Ещё впереди

- §8 Content + Telegram (draft/preview/fake → real publish с OK).
- §9 Compose E2E / backup / doctor расширения.
- §10 Hermes compatibility (CLI contracts only).
- §11 отдельный `job-search-hermes` — отложен.

## Локальный runtime (ориентир)

| Сервис | Порт / заметка |
|---|---|
| Core | `127.0.0.1:18000` |
| Web | `127.0.0.1:18080` |
| HH noVNC | `127.0.0.1:6080` |
| HH OAuth publish | `127.0.0.1:8767` (контейнер); архивный redirect app — `:8765/callback` |
| Host HH proxy | `127.0.0.1:2080` (нужен для API с этой сети) |

Не коммитить: `services/hh/.env`, `services/hh/.local/**`, токены, cookies, profile.

## Решение по «го» / blockers

- **«Го»** = **T-UX-00.9** Gate R0 with product owner, или если скажешь явно другую задачу.
- Content/Telegram, browser HH apply, Scoring redesign — только по явной фразе,
  не default.
- **«OK на HH writes» уже дан**, но API-path сейчас бессмысленен без scopes /
  browser transport (не текущий next).
- Push/PR — только по явной просьбе.

## Как обновлять этот файл

После каждого завершённого зелёного среза (или явного запроса «обнови статус»):

1. Обновить дату и HEAD SHA.
2. Поправить таблицу вердикта и блок HH/блокеров по факту.
3. Держать блок «Главный продуктовый next» / текущий task согласованным с
   [`docs/R0_DESIGN.md`](docs/R0_DESIGN.md), пока активен R0.