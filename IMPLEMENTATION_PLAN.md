# План реализации Job Search Multirepo

**Revision:** 2  
**Basis:** UJM v1 + Product Backlog + Roadmap v1 + [`ARCHITECTURE_PLAN.md`](ARCHITECTURE_PLAN.md) rev. 2  
**Updated:** 2026-08-26 (R1.2 COMPLETE; R1.3 started)  
**Previous revision:** 1 (service bootstrap / multirepo transfer sequence)

Оперативный снимок: [`PROJECT_STATUS.md`](PROJECT_STATUS.md).  
Архитектура: [`ARCHITECTURE_PLAN.md`](ARCHITECTURE_PLAN.md).  
Gate R0: [`docs/R0_ACCEPTANCE.md`](docs/R0_ACCEPTANCE.md).

---

## Как читать этот документ

**Roadmap** задаёт продуктовый порядок этапов. **Implementation Plan** задаёт
**исполнимые инкременты**, Gates и проверки для ближайших product slices.

```text
Roadmap stage → selected PBI → US / TECH-US / DEBT-US
  → Acceptance Criteria → BDD/Gherkin (where useful)
  → Tasks → implementation → Gate
```

**Не является планом развития продукта:**

```text
Core → Web → HH → Scoring → OSINT → Content → Hermes
```

Это была очередь **переноса кода** из архива (rev. 1). Bootstrap largely
выполнен; продуктовый приоритет теперь Roadmap-driven.

**Декомпозиция сейчас:** ближайший execution slice — **R1 / PB-00**.
R1–R5 — execution sequence и Gate outcomes; детальные Tasks — при входе в stage.

---

## Продуктовая последовательность

```text
R0 — CLOSED (PB-UX-00, Gate 2026-08-22)
  ↓
Plan revisions (ARCHITECTURE_PLAN rev. 2, IMPLEMENTATION_PLAN rev. 2)  ← this revision
  ↓
PB-DATA-00 — COMPLETE (one-time owner bootstrap; isolated from product flow)
  ↓
R1 — HH connection + active resume / profile context (PB-00 + minimal PB-01)
  ↓
R2 — find → score in Vacancy → decide (PB-01…PB-04, initial PB-11)
  ↓
R3 — outreach + response (PB-05…PB-07, PB-11 extension)
  ↓
R4 — hiring process (PB-08 + metrics)
  ↓
R5 — offer + finish search (PB-09, PB-10, final PB-11)
```

---

## Current baseline (implemented)

Компактный снимок **уже выполненного** — не дублирует `PROJECT_STATUS.md` целиком.

### Bootstrap / workspace

| Item | Status |
|---|---|
| Multirepo workspace, submodules, bootstrap/doctor | **Done** |
| Code inventory (`docs/inventory/*`, `make inventory-check`) | **Done** |
| Compose stack: postgres, core, web, scoring, searxng, osint, hh | **Done** |
| Workspace integration Gate (full E2E lock, compose-smoke polish) | **Partial** |

### R0 / PB-UX-00 — CLOSED

- Web: **Calm Dense Productivity**, primary scheme **dark** ([`DESIGN.md`](DESIGN.md))
- **5 top-level sections:** Vacancies, Journal, Metrics, People, Hypotheses
- Assessment / ScoringResult **contextual to Vacancy** (not standalone workspace)
- Gate R0: **ACCEPTED WITH NON-BLOCKING DEBT** (2026-08-22); Web **37 passed** @ `86f37cb`

### Core

- PostgreSQL 17 + Alembic (7 migrations)
- Entities + `/api/v1`: Company, Vacancy, Application, DailyMetric, Person,
  Hypothesis, Assessment
- Idempotent writes, OpenAPI, JSON CLI, contract/BDD tests
- Initial owner history was bootstrapped once; a clean install starts empty

### Web

- HTTP-only Core consumer; OSINT research proxy
- Working flows: vacancies, journal, metrics, people, hypotheses, dialogs
- System states (loading/empty/error/offline/notice); R0 IA accepted
- Does **not** launch HH or Scoring

### HH

- **Read-ready:** session/token on volumes, noVNC operator login, OAuth loopback,
  vacancy sync → Core, applications/metrics sync (fixture + live where scope allows)
- **Write path code:** dual-gate limited apply exists
- **Production apply:** **not ready** — applicant API scope returns **403** on
  `/negotiations`, `/resumes/mine` for current HH app; browser apply transport
  **not implemented** (decision point, not guaranteed API flow)

### Scoring

- **Basic executable pipeline:** JSON queue worker, host Ollama, raw store in
  `scoring-state`, normalized Assessment → Core
- **Not** target R2 scoring architecture (no CandidateProfile context, policy
  versioning, ranking, batch vs detailed modes)

### OSINT

- **On-demand research:** website CLI, people-research, vacancy mirrors, confirm → Core
- Web HTTP: people-research, mirrors, people-confirm
- Provenance local; **not** auto-triggered per vacancy (target R3 UX deferred)

### Content / Hermes

- **Content:** submodule stub, empty, not in compose — **deferred**
- **Hermes:** adjacent/later — **outside near-term execution queue**

---

## Rev. 1 sections — reclassification

| Rev. 1 section | Classification | Notes |
|---|---|---|
| §0A Workspace foundation | **DONE** | submodules, bootstrap, doctor, ADR |
| §0B Integration workspace | **PARTIAL** | dev/test/backup exist; full compose-smoke lock not closed |
| §1 Code inventory | **DONE** | `docs/inventory/*`; distinct from **DATA-00.1** entity inventory |
| §2 Repository skeletons | **PARTIAL** | Core/Web/HH/Scoring/OSINT ready; Content stub |
| §3 Core entities | **DONE** | all listed increments shipped |
| §4 Web MVP | **DONE** | + R0 redesign closed |
| §5 HH read-path | **DONE** | read-gate verified |
| §5 HH write/apply | **PARTIAL** | code dual-gate; production blocked by external API scope |
| §6 Scoring basic pipeline | **PARTIAL** | worker exists; R2 foundation not started |
| §7 OSINT research | **PARTIAL** | on-demand capability; R3 product flow not built |
| §8 Content/Telegram | **DEFERRED** | superseded as next step |
| §9 Workspace E2E flow | **PARTIAL** | old target flow **SUPERSEDED**; integration hardening still useful later |
| §10 Hermes compatibility | **DEFERRED** | not near-term |
| §11 job-search-hermes project | **DEFERRED** | |
| «Core→Web→HH→…» sequence | **SUPERSEDED** | replaced by Roadmap sequence |
| «OSINT enriches company after scoring» | **SUPERSEDED** | manual OSINT after user decision (R3) |
| «Next: Content §8» | **SUPERSEDED** | next = R1 / PB-00 |
| Legacy SQLite auto-import | **DONE** | one-time owner bootstrap; isolated |
| Standalone Assessments Web workspace | **SUPERSEDED** | IA correction R0; contextual in Vacancy |

---

## Active implementation queue

**После этой revision — буквальный порядок работ:**

1. **R1** decomposition of PB-00 (+ minimal PB-01) → R1 implementation → **Gate R1**
2. **R2** (after R1 Gate) — see § R2 below

**Не в очереди:** Content next · Scoring foundation before R2 · Hermes next.

---

## PB-DATA-00 — historical result

One-time owner bootstrap migration completed and isolated from canonical
product flow. A new clone of `job_search_ref` does not require the old
monolith, SQLite, or migration tooling. Details live outside this repository.

---

## R1 — HH connection + active resume

**PBI:** PB-00 + minimally necessary PB-01.  
**Decomposition:** [`docs/R1_PB00_DECOMPOSITION.md`](docs/R1_PB00_DECOMPOSITION.md)  
**Implementation:** **R1.1 COMPLETE**; **R1.2 COMPLETE** (OWNER ACCEPTED 2026-08-26);
**R1.3 IN PROGRESS** (browser RO resume list); R1.4–R1.6 not started; **Gate R1 OPEN**.

**Product outcome:** operator connects HH, sees account context, selects **active
HH resume**, with local linkage to profile/resume context for downstream R2.

### Audit snapshot

| Capability | Class |
|---|---|
| Session / OAuth / noVNC login CLI | **IMPLEMENTED** |
| Product-facing connection status (Web) | **IMPLEMENTED** (R1.1) |
| HH account/profile (`/me`) | **IMPLEMENTED** (R1.2 COMPLETE); official API |
| Resume list product surface | **IN PROGRESS** (R1.3 browser RO); API **EXTERNAL_BLOCKED** |
| Active resume select/persist | **MISSING** |
| CandidateProfile / ProfileVersion | **MISSING** |
| Unified action-required states | **PARTIAL** (R1.1 connection + R1.2 profile codes) |
| Web HH context UI | **PARTIAL** (connection + account; resume UI in R1.3) |

### Stories (summary)

| ID | Intent |
|---|---|
| **US-00.1** | Understand HH connection state — **DONE (R1.1)** |
| **US-00.2** | See HH account/profile — **DONE (R1.2)** |
| **US-00.3** | List HH resumes — **IN PROGRESS (R1.3)** |
| **US-00.4** | Select active HH resume |
| **US-00.5** | Restore active resume after restart |
| **US-00.6** | Explicit action-required (401/expired/CAPTCHA/403) |
| **US-01.1** | Minimal local CandidateProfile/ProfileVersion linkage |

TECH-US / DEBT-US / AC / BDD: see decomposition doc.  
**TECH-US-00.2** live probe: **DONE** 2026-08-25.

### Execution sequence

| Increment | Outcome |
|---|---|
| **R1.1** | Operator-visible HH connection/session status — **COMPLETE** (OWNER ACCEPTED) |
| **R1.2** | Current HH profile/account context via official `GET /me` — **COMPLETE** (OWNER ACCEPTED) |
| **R1.3** | Resume list via **authenticated browser read-only** — **IN PROGRESS** |
| **R1.4** | Active HH resume selection persisted |
| **R1.5** | Minimal CandidateProfile / ProfileVersion linkage in Core |
| **R1.6** | Unified recovery / action-required states |
| **R1.A** | Acceptance evidence → **Gate R1** |

**Next:** implement **R1.3**.  
**Gate critical path:** R1.3 browser resume list (403 error UX alone ≠ Gate CLOSED).  
**Gate R1:** **OPEN**.

### External constraint (not «debt»)

Live probe (usable OAuth session, 2026-08-25):

- `GET /me` → **200 SUPPORTED**
- `GET /resumes/mine` → **403 EXTERNAL_BLOCKED** (`forbidden`)
- `GET /negotiations` → **403** (not R1 scope; confirms DEBT-US-00.4)

**Owner decision R1.3:** authenticated browser session, **read-only** own resume list
(not apply/edit/negotiations/CAPTCHA bypass). Do **not** invent an API 403 bypass.

### Gate R1

**A.** Explicit 403/401/CAPTCHA handling is mandatory AC.  
**B.** Closing Gate still requires a **supported** path that actually lists resumes
and supports active-resume + linkage.

**Current official-API verdict:** Gate R1 **BLOCKED BY EXTERNAL CONSTRAINT** on
the resume-list leg until browser RO transport (or HH app permission change)
is implemented — without R2.

---

## R2 — Find → score → decide

**PBI:** PB-01, PB-02, PB-03, PB-04, initial PB-11.

**User chain:**

```text
profile/resume context
  → vacancy ingestion / normalization / dedupe
  → scoring
  → score + verdict in Vacancy (no Assessments workspace)
  → ranking
  → scoring details in Vacancy expand
  → explicit user decision (separate from LLM verdict)
```

Decompose at R2 entry into vertical increments. High-level sequence:

| Phase | Focus |
|---|---|
| **R2.1** | Vacancy ingestion/normalization improvements (PB-01/02) |
| **R2.2** | **SCORING_SERVICE_FOUNDATION** (PB-03) — see below |
| **R2.3** | Score/verdict/ranking in Vacancy Web context |
| **R2.4** | Scoring details UX in Vacancy |
| **R2.5** | User decision on Vacancy (PB-04) |
| **R2.6** | Initial analytics slice (PB-11) |

### SCORING_SERVICE_FOUNDATION (R2.2 — not started)

**Do not implement until R2.** Before implementation:

- create `docs/SCORING_SERVICE.md` (or `services/scoring/docs/SCORING_SERVICE.md`)
- ADR(s) only for truly fundamental decisions

**Foundation scope (minimal):**

```text
Vacancy + CandidateProfile + scoring policy → Ollama → canonical ScoringResult → Core Assessment
```

**Later increments (not in foundation):**

- deterministic/hard signals
- embeddings / retrieval (signals, not automatic verdict)
- fast batch scoring vs detailed analysis
- cache / reproducibility improvements
- policy versioning separate from model and profile version

**Canonical output:** score + verdict (`apply` / `maybe` / `skip` conceptually).

Current basic worker is **bootstrap only** — do not treat as R2 architecture.

### Gate R2

Operator can ingest vacancies, run scoring with profile context, see score/verdict
and details in Vacancy, rank results, and record **explicit user decision**
distinct from LLM recommendation.

---

## R3 — Outreach + response

**PBI:** PB-05, PB-06, PB-07, PB-11 extension.

**Target chain:**

```text
user decision = pursue
  → channel HH / direct / both
  → if direct: user manually triggers OSINT
  → automated people/contact research
  → outreach action recorded
  → response → next action
```

OSINT is **optional** and **manual** — not automatic for every Vacancy.

Existing OSINT on-demand capability is **input** to R3; product flow and outreach
recording are **not built**.

**Gate R3 (compact):** pursue decision leads to channel choice, optional OSINT,
recorded outreach, and response tracking in Core/Web.

---

## R4 — Hiring process

**PBI:** PB-08 + related metrics.

**Outcome:** active hiring processes with stages, meetings/test tasks, notes,
next action/deadline.

Detailed domain model — **future decomposition at R4 entry**. No schema design now.

**Gate R4 (compact):** operator tracks at least one active hiring process end-to-end
in product UI.

---

## R5 — Offer + finish search

**PBI:** PB-09, PB-10, final PB-11.

**Outcome:** offer comparison, accept/decline, start date, close SearchCycle,
final analytics.

Do not pre-design Offer schema beyond accepted product semantics.

**Gate R5 (compact):** search cycle can be closed with offer outcome and summary metrics.

---

## Debt and external constraints

| Class | Examples | Treatment |
|---|---|---|
| **A. Blocking next slice** | None known for R1 start | Track at R1 entry |
| **B. Non-blocking implementation debt** | duplicate smoke/demo Core rows; browser apply transport missing | Fix when relevant slice needs it |
| **C. Documentation drift** | old rev.1 «next Content»; volume name drift | Addressed by rev. 2 |
| **D. Housekeeping** | untracked R0 screenshot sets, prompts | Optional cleanup; not blocking |
| **External constraint** | HH API 403 on negotiations/resumes | Document in R1; not DEBT-US by default |
| **Non-blocking (Gate R0)** | cursor-rule test / `12-no-choice-menus.mdc`; `panel-eyebrow` naming | DEBT-US only if slice needs it |

Do not convert every tail into DEBT-US.

---

## Content and Hermes

| Area | Treatment |
|---|---|
| **Content / Telegram** (old §8) | **DEFERRED** — not current product slice; superseded as «next step» |
| **Hermes compatibility** (old §10) | **DEFERRED** — adjacent tooling |
| **job-search-hermes** (old §11) | **DEFERRED** — separate future project |

May re-enter plan when Roadmap explicitly schedules them.

---

## Workspace integration (residual)

Old §9 target flow **superseded**. Remaining useful work (**PARTIAL**, not next):

- compose-smoke / version lock polish
- backup/restore runbook verification
- doctor extensions

Execute in parallel only if it does not block R1.

---

## Gates summary

| Gate | Observable outcome |
|---|---|
| **Gate R0** | **CLOSED** 2026-08-22 — dark 5-section Web, Assessment contextual, 37 tests |
| **Gate PB-DATA-00** | **CLOSED** — one-time owner bootstrap isolated from product flow |
| **Gate R1** | HH connected; active resume + local linkage; blocked paths documented |
| **Gate R2** | Score/verdict/ranking/decision in Vacancy context with profile-aware scoring |
| **Gate R3** | Pursue → channel → optional OSINT → outreach → response |
| **Gate R4** | Hiring process tracking |
| **Gate R5** | Offer + SearchCycle closure + final analytics |

---

## Current next step

**R1.3** — own HH resume list via authenticated browser **read-only** transport
(owner decision; official `/resumes/mine` remains EXTERNAL_BLOCKED).

R1.1 and R1.2 are **COMPLETE**. **Gate R1** remains **OPEN** until later slices.

Do not start Scoring foundation, Content, or Hermes until R1 Gate
(or documented PO waiver).

Оперативный снимок и HEAD SHA: [`PROJECT_STATUS.md`](PROJECT_STATUS.md).
