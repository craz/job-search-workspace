# План реализации Job Search Multirepo

**Revision:** 3  
**Basis:** UJM v1 + Product Backlog + Roadmap v1 + [`ARCHITECTURE_PLAN.md`](ARCHITECTURE_PLAN.md) rev. 3  
**Updated:** 2026-08-28 (R2.2 CLOSED; R2.3 architecture ready for owner review)  
**Previous revision:** 2 (R1 closed; R2.2 decomposition)

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

- **Bootstrap pipeline:** JSON queue worker, host Ollama, raw store in
  `scoring-state`, normalized Assessment → Core
- **R2.3 foundation designed** — see [`docs/SCORING_SERVICE.md`](docs/SCORING_SERVICE.md);
  **implementation NOT STARTED**
- **Not yet:** scoring-ready Core context assembly, ScoringPolicy versioning,
  `LlmBackend`, HTTP product surface, current-result identity, R2.4 batch UI

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
**Implementation:** **R1.1–R1.6 COMPLETE · PUSHED**;
**R1.A ACCEPTED**; **Gate R1 CLOSED** (OWNER ACCEPTED 2026-08-27).

**Product outcome:** operator connects HH, sees account context, selects **active
HH resume**, with local linkage to profile/resume context for downstream R2.

### Audit snapshot

| Capability | Class |
|---|---|
| Session / OAuth / noVNC login CLI | **IMPLEMENTED** |
| Product-facing connection status (Web) | **IMPLEMENTED** (R1.1) |
| HH account/profile (`/me`) | **IMPLEMENTED** (R1.2 COMPLETE); official API |
| Resume list product surface | **IMPLEMENTED** (R1.3 COMPLETE · PUSHED); browser RO |
| Active resume select/persist | **IMPLEMENTED** (R1.4 COMPLETE); HH state file |
| CandidateProfile / ProfileVersion | **IMPLEMENTED** (R1.5 COMPLETE · PUSHED); **identifier-only**, not scoring-ready |
| Unified action-required states | **IMPLEMENTED** (R1.6 COMPLETE; OWNER ACCEPTED) |
| Web HH context UI | **PARTIAL** (connection + account + resume + recovery UX + debug linkage line) |

### Stories (summary)

| ID | Intent |
|---|---|
| **US-00.1** | Understand HH connection state — **DONE (R1.1)** |
| **US-00.2** | See HH account/profile — **DONE (R1.2)** |
| **US-00.3** | List HH resumes — **DONE (R1.3)** |
| **US-00.4** | Select active HH resume — **DONE (R1.4)** |
| **US-00.5** | Restore active resume after restart — **DONE (R1.4)** |
| **US-00.6** | Explicit action-required (401/expired/CAPTCHA/403) — **DONE (R1.6)** |
| **US-01.1** | Minimal local CandidateProfile/ProfileVersion linkage — **DONE (R1.5)** |

TECH-US / DEBT-US / AC / BDD: see decomposition doc.  
**TECH-US-00.2** live probe: **DONE** 2026-08-25.

### Execution sequence

| Increment | Outcome |
|---|---|
| **R1.1** | Operator-visible HH connection/session status — **COMPLETE** (OWNER ACCEPTED) |
| **R1.2** | Current HH profile/account context via official `GET /me` — **COMPLETE** (OWNER ACCEPTED) |
| **R1.3** | Resume list via **authenticated browser read-only** — **COMPLETE · PUSHED** (OWNER ACCEPTED) |
| **R1.4** | Active HH resume selection persisted — **COMPLETE · PUSHED** (OWNER ACCEPTED) |
| **R1.5** | Minimal CandidateProfile / ProfileVersion linkage in Core — **COMPLETE · PUSHED** (OWNER ACCEPTED; identifier-only) |
| **R1.6** | Unified recovery / action-required states — **COMPLETE · PUSHED** (OWNER ACCEPTED) |
| **R1.A** | Integrated acceptance / Gate evidence — **ACCEPTED** → **Gate R1 CLOSED** |

**R1.5 architecture note:** linkage is `ProfileVersion` ↔ HH `external_resume_id`
only. Resume **content** snapshot is **not** in R1.5. **PB-03 Scoring** must not
consume R1.5 as candidate text; **R2 / full PB-01** must add local resume
snapshot/version first.

**Next:** not started — R2 awaits explicit owner start.  
**Gate R1:** **CLOSED**. R2 **NOT STARTED**.
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

**Current official-API resume list:** still **403 EXTERNAL_BLOCKED**.  
**Supported product resume path:** browser read-only (R1.3).  
**R1.A:** ACCEPTED → **Gate R1 CLOSED** (OWNER ACCEPTED 2026-08-27). R2 **NOT STARTED**.

---

## R2 — Find → score → decide

**PBI:** PB-01, PB-02, PB-03, PB-04, initial PB-11.  
**Canonical SoT:** Google Drive **Job Search** → Roadmap / R2 tab.  
**Decomposition (R2.1):** [`docs/R2_PB01_DECOMPOSITION.md`](docs/R2_PB01_DECOMPOSITION.md).

**Status:** Gate R1 **CLOSED**. R2.2 **CLOSED** (R2.2.A integrated acceptance).  
**R2.3:** architecture / decomposition **READY FOR OWNER REVIEW** — **NOT STARTED**.

**User chain:**

```text
local ResumeVersion (working resume content)
  → vacancy ingestion / normalization / dedupe
  → scoring against that ResumeVersion
  → score + verdict in Vacancy (no Assessments workspace)
  → ranking
  → scoring details in Vacancy expand
  → explicit user decision (separate from LLM verdict)
```

### Execution sequence (canonical)

| Phase | Focus | Status |
|---|---|---|
| **R2.1** | Local ResumeVersion / content snapshot of active HH resume | **COMPLETE · PUSHED** |
| **R2.2** | SearchRun + resume_suitable acquisition + ingest/dedupe/temporal + Web primary UX | **COMPLETE · PUSHED** (evidence `R2_2_A`) |
| **R2.3** | **SCORING_SERVICE_FOUNDATION** (PB-03) | architecture **READY FOR REVIEW**; impl **NOT STARTED** |
| **R2.4** | Mass score/verdict in Vacancy + list prioritization | NOT STARTED |
| **R2.5** | Detailed scoring in Vacancy context | NOT STARTED |
| **R2.6** | Explicit user decision (PB-04) | NOT STARTED |
| **R2.7** | Basic PB-11 metrics slice | NOT STARTED |
| **Gate R2** | Owner Gate decision after R2.1–R2.7 evidence | OPEN |

### R2.1 — Local ResumeVersion (accepted decisions)

Detailed US / TECH-US / slices: [`docs/R2_PB01_DECOMPOSITION.md`](docs/R2_PB01_DECOMPOSITION.md).

**Product outcome:** immutable local snapshot of the working HH resume content,
manual sync only, usable later by PB-03.

**Key decisions:** manual sync only; no fake empty versions; return to prior
resume reuses latest local copy; allowlist fields (no contacts/PII); JSONB
schema-versioned snapshot; candidate-context shows metadata only; keep
`ProfileVersion`=`r1-default`; **no** mandatory active-pointer table
(current = active HH link + latest `ResumeVersion` for that `external_resume_id`).

**Internal slices (do not start until owner says):** R2.1.1 → R2.1.5.

### SCORING_SERVICE_FOUNDATION (R2.3)

**Prerequisite:** R2.1 ResumeVersion + R2.2 scoring-ready Vacancy ingest — **met**.

**Canonical design:** [`docs/SCORING_SERVICE.md`](docs/SCORING_SERVICE.md)  
**ADRs:** 005 (boundary), 006 (policy/result identity), 007 (LlmBackend/Ollama)

**Foundation scope (minimal):**

```text
Vacancy + scoring-ready ResumeVersion + ScoringPolicy
  → LlmBackend (Ollama)
  → structured ScoringResult
  → Core Assessment (with provenance / current-result identity)
```

**Implementation slices (do not start until owner accepts architecture):**

| Slice | Focus |
|---|---|
| **R2.3.1** | Canonical contracts: ScoringPolicy, ScoringResult schema, `scoring_identity_hash`, Core Assessment provenance extension (migration) |
| **R2.3.2** | Scoring-ready context assembly: Core GET vacancy-by-id, resume content read; retire private `data/resume.txt` as sole source |
| **R2.3.3** | `LlmBackend` protocol + `OllamaBackend` (`/api/generate`; embed interface stub) |
| **R2.3.4** | Single-vacancy **fast** scoring E2E: minimal HTTP + worker path + Core write |
| **R2.3.5** | Job lifecycle hardening: current-result skip, re-score on `content_hash` change, observability |
| **R2.3.A** | Integrated foundation acceptance (live + tests) |

**Later (not R2.3):** deterministic signals implementation, embeddings retrieval,
batch enqueue (R2.4), detailed mode UX (R2.5).

**Canonical output:** score 0–100 + verdict (`apply` / `maybe` / `skip`). Bootstrap
worker is **adaptation baseline**, not target architecture.

### Gate R2

Operator can ingest vacancies, run scoring with **local ResumeVersion** context,
see score/verdict and details in Vacancy, rank results, and record **explicit
user decision** distinct from LLM recommendation.

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
| **Gate R1** | **CLOSED** 2026-08-27 — HH connected; active resume + id-only linkage; recovery; `/resumes/mine` EXTERNAL_BLOCKED documented |
| **Gate R2** | Score/verdict/ranking/decision in Vacancy context with profile-aware scoring |
| **Gate R3** | Pursue → channel → optional OSINT → outreach → response |
| **Gate R4** | Hiring process tracking |
| **Gate R5** | Offer + SearchCycle closure + final analytics |

---

## Current next step

**R2.2 CLOSED · PUSHED.**  
**R2.3 architecture / decomposition — READY FOR OWNER REVIEW.**  
**R2.3 implementation — NOT STARTED** (wait for owner ACCEPT on architecture).

Do not start R2.3.1 until owner accepts R2.3 design.


Оперативный снимок и HEAD SHA: [`PROJECT_STATUS.md`](PROJECT_STATUS.md).
