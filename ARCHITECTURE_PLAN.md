# План архитектуры Job Search Multirepo

**Revision:** 2  
**Aligned with:** UJM v1 + Product Backlog + Roadmap v1  
**Updated:** 2026-08-22  
**Previous revision:** 1 (initial multirepo split plan, workspace bootstrap era)

Продуктовый workspace `job_search_ref` самодостаточен. Репозитории не
импортируют Python-код друг друга и не получают прямой доступ к чужим хранилищам.

Нормативный визуальный слой Web — [`DESIGN.md`](DESIGN.md). Операционный статус —
[`PROJECT_STATUS.md`](PROJECT_STATUS.md). Gate R0 — [`docs/R0_ACCEPTANCE.md`](docs/R0_ACCEPTANCE.md).

## 1. Границы продукта и системы

Job Search — **single-user personal product** для одного оператора на доверенной
локальной машине.

**Не планируется и не проектируется:**

- таблица пользователей Job Search;
- RBAC / roles;
- tenant / multi-tenant model;
- product login / session для Web.

**HeadHunter authentication/session** — интеграционная concern сервиса HH, не
auth-модель продукта. Web и Core HTTP API опираются на модель **trusted local
operator**: сервисы на loopback / внутренней Docker-сети без application-level auth.

**Hermes** — adjacent/later tooling; не драйвер текущей архитектуры. Его
контейнеризация и перенос конфигурации отложены.

**Целевые сервисы (conceptual):**

| Сервис | Роль |
|---|---|
| **Core** | Каноническая доменная persistence и `/api/v1` |
| **Web** | Локальный UI; HTTP consumer Core (+ OSINT research view) |
| **HH** | Адаптер HeadHunter (OAuth, browser, sync, gated apply) |
| **Scoring** | Оценка вакансий через host Ollama → Assessment в Core |
| **OSINT** | On-demand исследование людей/сайтов; provenance у себя |
| **Content** | Черновики и Telegram (будущий этап; submodule stub) |

## 2. Продуктовая последовательность (Roadmap)

**Старый порядок «Core → Web → HH → Scoring → OSINT → Content» — не Roadmap.**
Это была последовательность **переноса кода** из архива; она largely выполнена
как инженерный bootstrap, но **не определяет продуктовый приоритет**.

**Актуальная продуктовая цепочка:**

```text
R0 — CLOSED (PB-UX-00, Gate R0 2026-08-22)
  ↓
revision ARCHITECTURE_PLAN.md (this document, rev. 2)
  ↓
revision IMPLEMENTATION_PLAN.md
  ↓
PB-DATA-00 — COMPLETE (one-time owner bootstrap; isolated)
  ↓
R1 — HH connection + active resume / profile context
  ↓
R2 — find → score in Vacancy context → user decision (PB-03, PB-04)
  ↓
R3 — outreach + response (optional manually-triggered OSINT)
  ↓
R4 — hiring process
  ↓
R5 — offer + finish search
```

**User-centric flow (target):**

```text
HH / profile context
  → vacancy ingestion
  → scoring (Scoring service → Assessment in Core)
  → user decision on Vacancy
  → channel selection (HH / direct / both)
  → optional manually-triggered OSINT
  → outreach recorded
  → response → hiring → offer → search completion
```

Устаревшая формулировка «HH → Core → Scoring → OSINT enriches company → Web»
**не соответствует** UJM/Roadmap: OSINT не запускается silently для каждой
вакансии; enrichment компании — часть on-demand OSINT, не автоматический prelude.

## 3. Workspace и репозитории

### `job-search-workspace`

Управляющий репозиторий (не продуктовый):

- `.gitmodules`, gitlinks с проверенными SHA;
- `compose.yaml`, Make (`bootstrap`, `dev`, `doctor`, `test`, `backup`, `restore`);
- архитектурная и процессная документация.

Developer experience: `make dev` поднимает stack; Web на loopback; HH Chromium
через noVNC; hot reload для Core/Web/OSINT src mounts.

Имена долгоживущих deployment-инстансов — [`NAMING_CONVENTION.md`](NAMING_CONVENTION.md).

### Продуктовые репозитории (`services/*`)

| Repo | Владение | Статус (rev. 2) |
|---|---|---|
| `job-search-core` | PostgreSQL, домен, Alembic, `/api/v1`, JSON CLI | **Implemented** |
| `job-search-web` | Static SPA + HTTP proxy | **Implemented** (R0 IA accepted) |
| `job-search-hh` | HH integration, Chromium, volumes | **Implemented** (read-ready) |
| `job-search-scoring` | Queue, Ollama, Assessment writeback | **Partial** (basic pipeline) |
| `job-search-osint` | Research API/CLI, provenance cache | **Implemented** (on-demand) |
| `job-search-content` | Drafts, Telegram | **Stub** (empty submodule, not in compose) |
| `job-search-hermes` | Audit CLI consumer | **Deferred** |

## 4. Runtime и постоянное состояние

Docker Compose (`compose.yaml`) поднимает:

- `postgres` — PostgreSQL 17;
- `core`, `web` — опубликованы на loopback хоста;
- `scoring` — **host network**, long-running worker (`cli run`);
- `searxng` — search backend для OSINT (infra, не product service);
- `osint` — internal HTTP :8081;
- `hh` — browser runtime, noVNC, OAuth loopback.

**Content не в compose** до реализации сервиса.

| Volume | Владелец | Содержимое |
|---|---|---|
| `postgres-data` | PostgreSQL/Core | Основная БД |
| `hh-profile` | HH | Chromium profile, cookies |
| `hh-state` | HH | Tokens, snapshots, lock state |
| `scoring-state` | Scoring | JSON queue, raw model responses, lease state |
| `osint-cache` | OSINT | Provider responses, provenance |
| `searxng-cache` | SearXNG | Search cache |

`docker compose down` volumes сохраняет. Backup: `pg_dump` / volume export через
workspace Make (см. runbooks).

**Фоновая обработка:** только Scoring scheduler/worker (local JSON queue + file
lock). HH sync и OSINT — **on-demand** (CLI exec или HTTP request). Нет Kafka,
Redis, Celery, vector DB или Kubernetes в текущей архитектуре.

**Ollama** на хосте (`127.0.0.1:11434`); Scoring через host network. GPU не в
контейнере Scoring. Все local AI inference — через Ollama.

**Chromium** — только в HH-контейнере; один profile + lock для login/sync/apply.

## 5. PostgreSQL и владение данными

PostgreSQL 17, SQLAlchemy 2.x, Alembic. **Только Core** имеет credentials
прикладного пользователя PostgreSQL. Postgres **не** публикуется на host.

Другие сервисы **не** выполняют SQL к domain tables; только HTTP/JSON CLI к Core
(или собственное private state).

**Source of truth по сущностям:**

| Entity / artifact | Owner | Notes |
|---|---|---|
| Company, Vacancy, Application | Core | `(source, external_id)` uniqueness |
| DailyMetric | Core | |
| Person, Hypothesis | Core | |
| Assessment / ScoringResult | Core | Written by Scoring; read by Web via Core API |
| HH tokens, cookies, profile | HH volumes | Never in Core |
| Scoring queue, raw LLM output | Scoring state volume | Normalized result → Core only |
| OSINT raw/proposed findings | OSINT cache | Confirmed → Core HTTP |
| Content drafts, Telegram IDs | Content (future) | Not in Core |

**Implemented Core schema** (Alembic): `Company`, `Vacancy`,
`Application`, `DailyMetric`, `Person`, `Hypothesis`, `Assessment`,
plus R1.5 `CandidateProfile` / `ProfileVersion` / `ActiveHhResumeLink`
(**identifier-only** HH resume linkage — not resume body content).

**Target concepts (Roadmap; детальные схемы — позже):**

- `SearchProfile` + `SearchRun` — R2.2 DECOMPOSITION (READY FOR OWNER ACCEPTANCE):
  minimal persisted search criteria (**not** derived from ResumeVersion);
  SearchRun stores immutable criteria snapshot + run counts/status;
  vacancy ingest uses `(source, external_id)` upsert + source `content_hash`;
  see [`docs/R2_2_DECOMPOSITION.md`](docs/R2_2_DECOMPOSITION.md);
- richer `CandidateProfile` / `ProfileVersion` (beyond R1/R2.1 minimum);
- `ResumeVersion` (local **content** snapshot) — R2.1 **COMPLETE**:
  separate immutable Core entity (JSONB schema-versioned); R1.5 remains
  identifier-only; current local copy = active HH link + **latest**
  `ResumeVersion` for that `external_resume_id` (no mandatory pointer table);
  `ProfileVersion` stays `r1-default` through R2.1; before **PB-03 / R2.3 Scoring**
  this snapshot must exist;
- user **decision** on Vacancy (отдельно от LLM verdict — R2/PB-04);
- hiring pipeline, `Offer`, `SearchCycle` (R4–R5).

Архитектурное правило: **не проектировать unfinished schemas здесь**; фиксируем
ownership и семантические связи. Core остаётся каноническим store нормализованных
domain entities, если иное не будет принято отдельным ADR.

**Greenfield note:** a new PostgreSQL is created empty via Alembic. Owner history
was bootstrapped once before R1; it is not an install or runtime step.

## 6. Публичные контракты

### Core HTTP API (`/api/v1`)

Ресурсы: `vacancies`, `companies`, `applications`, `metrics`, `hypotheses`,
`people`, `assessments`.

Записывающие запросы интеграций — **idempotency key**. Ошибки: stable machine
code + `trace_id`. OpenAPI — source of truth (`services/core`).

### JSON CLI

`--output json`, envelope `contract_version` / `ok` / `data` / `errors`. Нет
shared Python package между репами; contract tests на OpenAPI/JSON Schema.

### Web proxy

Web re-exposes Core routes and OSINT research routes (`/api/v1/osint/*`) without
own DB. Web **не** orchestrates HH or Scoring launch in текущей версии.

## 7. Core

Core — **canonical application/domain layer**:

- domain rules, application services;
- Alembic migrations;
- FastAPI `/api/v1` + machine CLI.

Core **не знает** о Playwright, Telegram, Ollama, конкретных OSINT providers.

**Assessment / ScoringResult** в Core — результат оценки **Vacancy** (score,
verdict, reason, risk, action, model metadata). Это domain entity, не UI section.

## 8. Web (R0 accepted IA)

Web следует [`DESIGN.md`](DESIGN.md) — Calm Dense Productivity, **dark primary**.

**Top-level workspaces (5):**

1. Vacancies  
2. Journal  
3. Metrics  
4. People  
5. Hypotheses  

**Assessment contextual to Vacancy** — не standalone workspace:

```text
Vacancy → score + verdict summary → scoring details → user decision (R2+)
```

R0: Web client-joins `/api/v1/assessments` при загрузке Vacancies; score/verdict
в row; reason/risk/action в expand. Manual assessment dialog removed; API intact.

Детальный CSS/design-system в ARCHITECTURE_PLAN **не** дублируется — см. DESIGN.md.

## 9. HH service (R1 architectural dependency)

HH — **external HeadHunter adapter**:

- OAuth/token + browser session (noVNC operator login);
- vacancy sync → Core;
- applications/metrics sync (API where scope allows, fixtures/fallback otherwise);
- dual-gated apply (`JOB_SEARCH_HH_EXTERNAL_WRITES_ENABLED` + CLI flag).

**R1 product prerequisite:**

```text
HH session/auth
  → current HH account/profile
  → resume list
  → active HH resume
  → linkage to local CandidateProfile / ProfileVersion (R1.5: id only)
  → unified recovery / action-required states (R1.6)
  → (R2.1) local ResumeVersion content snapshot (manual sync) before R2.3 / PB-03 Scoring
```

**Scope reality (verified):** applicant token may be alive (`GET /me` → 200), но
`GET /negotiations`, `GET /resumes/mine` → **403** для текущего HH app permissions.
Production API apply blocked until scope expansion **or** browser apply transport.
**Не обещать** API operations beyond current HH application capabilities.

PB-00 (live HH ingestion) — architectural dependency для R1; см. HH runbooks.

Volumes `hh-state`, `hh-profile` — exclusive HH ownership.

## 10. Scoring service (R2)

Scoring — **standalone service** (не часть Core, не top-level Web workspace).

**Target conceptual pipeline (R2; detailed design — later artifact):**

```text
Vacancy + CandidateProfile
  → deterministic signals
  → semantic signals / retrieval (embeddings as signals, not automatic verdict)
  → relevant profile context
  → LLM score (host Ollama)
  → ScoringResult → Core Assessment
```

**Rules:**

- Canonical output: **score + verdict** (`apply` / `maybe` / `skip` conceptually).
- Fast batch score vs detailed analysis — **different use cases**.
- Scoring **policy versionable** separately from model and CandidateProfile version.
- Web presents score/verdict **in Vacancy context**; user decision **separate**
  from LLM recommendation (R2/PB-04).

**Implemented now (basic):**

- JSON file queue in `scoring-state`;
- worker reads Vacancy from Core HTTP;
- Ollama call; raw stored locally;
- normalized `POST /api/v1/assessments` with `source: job-search-scoring`.

**Not in scope of this document:** full `SCORING_SERVICE_FOUNDATION` — см. future
`services/scoring/docs/SCORING_SERVICE.md` and ADRs. Rev. 2 фиксирует boundary,
principles, reproducibility expectation (raw + normalized lineage), link requirement.

## 11. OSINT (R3 behavior)

OSINT — on-demand research; **не** silent auto-enrichment каждой вакансии.

**Target product flow:**

```text
User decides to pursue Vacancy
  → selects channel (HH / direct / both)
  → if direct path: user manually triggers OSINT
  → OSINT searches for relevant people / contact signals
  → findings keep provenance + confidence
  → user confirms person/contact
  → outreach recorded in Core (Application / Person)
```

**Implemented triggers:**

- CLI: website discover/confirm, people research, vacancy mirrors;
- Web HTTP: people-research, vacancy-mirrors, people-confirm (via OSINT API);
- SearXNG + fallback providers; evidence in `osint-cache`;
- unconfirmed proposals **never** written to Core.

Website discover/confirm — CLI-first (no website routes in OSINT HTTP API yet).

## 12. Content (later)

Planned: drafts, Telegram preview/publish, publication journal. Submodule exists
but **empty**; not in compose. Content reads public data via Core API; drafts and
Telegram tokens stay outside Core.

## 13. Historical bootstrap

Initial owner legacy data bootstrap completed before R1. Canonical architecture
has **no** runtime or setup dependency on a sibling monolith or SQLite archive.

## 14. Integration rules

| Concern | Decision |
|---|---|
| Inter-service calls | Synchronous HTTP/JSON CLI |
| Queues | Scoring local JSON queue only |
| Idempotency | Core write endpoints + integration keys |
| External IDs | `(source, external_id)` in Core |
| Failure/retry | Owner service retries (Scoring lease/retry; HH captcha stop) |
| AI backend | Host Ollama only (local) |
| Event bus | **Absent** — do not introduce without ADR |
| Security boundary | Loopback publish + trusted operator; no product auth layer |

## 15. Architecture status matrix

| Area | Implemented | Partial | Target / later |
|---|---|---|---|
| Workspace submodules + compose | ✓ | | |
| Core domain + PostgreSQL | ✓ | | |
| Web R0 UI + 5-section IA | ✓ | | |
| Assessment in Vacancy context (R0) | ✓ | | |
| HH read sync + session | ✓ | | |
| HH production API apply | | ✓ (dual-gate code; 403 scope) | browser transport option |
| Scoring basic pipeline | | ✓ | R2 full pipeline + policy versioning |
| OSINT on-demand research | ✓ | | R3 outreach-integrated UX |
| Content / Telegram | | | R? / §8 |
| PB-DATA-00 bootstrap | ✓ isolated | | one-time; not a product feature |
| CandidateProfile / active resume | | | R1 |
| User decision after scoring | | | R2/PB-04 |
| Hiring / Offer / SearchCycle | | | R4–R5 |
| Hermes integration | | | deferred |

## 16. Non-blocking debt (Gate R0)

Classified for tracking; **не reopen R0** unless blocker emerges:

| Category | Examples |
|---|---|
| Architecture mismatch | `ARCHITECTURE_PLAN` rev.1 listed Content in runtime; compose has no Content |
| Implementation debt | HH API 403 scope; no browser apply transport; duplicate demo Core rows |
| Documentation debt | `IMPLEMENTATION_PLAN.md` still service-order oriented; volume name drift (`scoring-cache` vs `scoring-state`) |
| Housekeeping | Untracked R0 screenshot sets; legacy CSS selectors (`#assessment-form`) |
| Test debt | Workspace cursor-rule test vs `12-no-choice-menus.mdc` |

Concrete DEBT-US items — only when product/engineering reason exists; not bulk-created here.

## 17. Тестирование и readiness

- Each repo installs/tests without archive `job_search` Python imports.
- No cross-repo Python imports or foreign volume access.
- Compose with empty volumes brings Core + consumers healthy.
- Web mutates domain only via Core API.
- HH dry-run does not POST apply; profile persists across restart.
- Scoring reaches host Ollama; handles unavailable gracefully.
- OSINT provenance local; confirmed entities idempotent to Core.
- Contract tests on Core OpenAPI and CLI JSON schemas.
- `make doctor` checks Docker, gitlinks, Core, Postgres, HH, Ollama as applicable.

Gate R0 Web acceptance: **37 tests passed** @ `86f37cb` (2026-08-22).

## 18. Безопасность

- Secrets via `.env` / Docker secrets — never in git.
- noVNC, OAuth, Core/Web on loopback or internal network.
- HH profile isolated from other containers.
- Logs exclude tokens, cookies, full cover letters.
- Destructive volume delete / restore requires explicit operator command.
- Hermes (when used) — no delete-history or bypass-limit actions.

---

**Next documentation step (not part of rev. 2):** keep [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) aligned with Roadmap (R1 → R2 …).
