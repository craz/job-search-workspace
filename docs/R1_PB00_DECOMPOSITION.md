# R1 / PB-00 — decomposition

**Status:** R1.1–R1.6 **COMPLETE · PUSHED**; **R1.A TECHNICAL / INTEGRATED PASS**; **Gate R1 READY FOR OWNER DECISION · OPEN**
**Date:** 2026-08-27  
**PBI:** PB-00 (primary) + minimal PB-01 slice for local linkage only  
**Prerequisite Gate:** PB-DATA-00 CLOSED  

Canonical execution pointer: [`IMPLEMENTATION_PLAN.md`](../IMPLEMENTATION_PLAN.md) § R1.  
This document owns the detailed US / AC / BDD / Tasks for R1 entry.

### R1.1 owner acceptance (manual)

**OWNER ACCEPTED** 2026-08-25 (manual review of http://127.0.0.1:18080/). Slice **COMPLETE**.

### R1.2 owner acceptance

**2026-08-26 REMARK (not ACCEPT):** live `/me` depended on a manual temporary
proxy-bridge because Docker cannot TCP to host loopback HTTP proxy. **Not COMPLETE.**

**Fix (2026-08-26):** documented `make up` / `make dev` path via
[`docs/runbooks/hh-docker-host-proxy.md`](../docs/runbooks/hh-docker-host-proxy.md)
(`hh-egress` + `.local` Unix socket). Temporary acceptance sidecar removed.

**OWNER ACCEPTED** 2026-08-26 (re-acceptance after host-proxy remarks + UI identity).
Slice **COMPLETE**. Transport: official API `GET /me` only (no browser).

### R1.3 owner acceptance

**OWNER ACCEPTED** 2026-08-26 (product review of http://127.0.0.1:18080/
«Резюме HH» with real resume titles after browser login). Slice **COMPLETE**.

Transport: authenticated **browser** session, **read-only** own resume list
(`GET /resumes/mine` remains 403 / EXTERNAL_BLOCKED). Web strip shows clean
titles; login CTA opens noVNC desktop; sticky mid-login CTAs auto-refresh.

---

## 1. Product goal

Operator has a trustworthy HeadHunter context:

```text
HH connection/session
  → HH account/profile
  → resume list
  → active HH resume
  → local CandidateProfile / ProfileVersion linkage
  → recovery / action-required states
  → Gate R1
```

**Out of R1:** full SearchProfile, scoring profile, multi-provider resumes,
vacancy ingestion redesign, browser apply productization, R2 scoring foundation.

---

## 2. Domain boundary (do not collapse)

| Concept | Meaning in R1 | Owner |
|---|---|---|
| **HH Account / Profile** | External HeadHunter account context (`/me` or documented substitute) | HH service (read) |
| **HH Resume** | External resume object from HH (`id`, title, …) | HH service (read) |
| **Active HH resume** | Exactly one selected external resume id for the operator (or explicit none) | HH + Core linkage |
| **CandidateProfile** | Local durable “who I am as a candidate” identity | Core |
| **ProfileVersion** | Local version row used as HH linkage target in R1.5 (identifier-only; content snapshot is R2 / full PB-01) | Core |
| **SearchProfile** | Search preferences / cycle context | **R2+** — not built in R1 |

`Application.resume_version` (existing Core free-text field on Journal) is **not**
the R1 linkage model. Do not overload it for active HH resume identity.

`Person` is company contact (OSINT) — **not** CandidateProfile.

---

## 3. Implementation audit (as of HH `1ec60bf`)

| Capability | Class | Evidence |
|---|---|---|
| HH connection / session (CLI) | **IMPLEMENTED** | `session.py` `session_status` / `auth_status`; CLI `session status`, `auth status|open-login|confirm|clear`; OAuth token store + loopback; specs/runbooks under `services/hh/docs/` |
| Operator noVNC login | **IMPLEMENTED** | `browser.py` + `auth open-login` / `confirm`; runbook `docs/runbooks/operator-novnc-login.md` |
| Product-facing connection status (Web / unified operator report) | **IMPLEMENTED** (R1.1) | `connection status` CLI + `GET /api/v1/connection`; Web header HH signal |
| HH account / profile (`GET /me`) | **IMPLEMENTED** (R1.2 COMPLETE) | `account status` + `GET /api/v1/account`; Web header identity; official `/me` |
| Resume list product surface | **IMPLEMENTED** (R1.3 COMPLETE · PUSHED) | Browser RO `resumes list` / `GET /api/v1/resumes`; official API still 403 |
| Active HH resume select / persist | **IMPLEMENTED** (R1.4 COMPLETE) | HH state `active_resume.json`; Web strip select/clear |
| CandidateProfile / ProfileVersion | **IMPLEMENTED** (R1.5 COMPLETE · PUSHED) | Identifier-only Core linkage; **not** resume content / not scoring-ready |
| Recovery / action-required (unified) | **DONE** | R1.6 OWNER ACCEPTED → COMPLETE |
| Web HH settings / resume UI | **PARTIAL** (R1.2–R1.5) | Resume strip + select; linkage line = acceptance/debug visibility |
| CAPTCHA bypass | **MISSING** (intentional) | `captcha_bypass: false`; apply stops — correct safety stance |

### External constraints (not DEBT-US)

**Live probe TECH-US-00.2 (2026-08-25)** — read-only, existing OAuth session
(`login_ready=true`, access token present, not expired; state under operator
`.local/hh-state`). No tokens/PII values recorded in git.

| Endpoint | HTTP | Classification |
|---|---|---|
| Session / token gate | n/a | **SUPPORTED** (usable) |
| `GET /me` | **200** | **SUPPORTED** |
| `GET /resumes/mine` | **403** (`errors[].type=forbidden`) | **EXTERNAL_BLOCKED** |
| `GET /negotiations` (status-only; not R1 scope) | **403** (`forbidden`) | **EXTERNAL_BLOCKED** |

`/me` identity fields present (shapes only): `id`, `first_name`, `last_name`,
`middle_name`, `email`, applicant/employer flags, plus `counters`
(`resumes_count`, `unread_negotiations`, `new_resume_views`) and URL hints
(`resumes_url`, `negotiations_url`). Resume **list** body was not returned
(403); no resume id/title fields observed via official API.

Code still: metrics maps resume 403 → `resumes_mine_forbidden`; applications
sync does **not** tolerate negotiations 403 (DEBT-US-00.4 confirmed live).

**R1.3 transport (owner decision, 2026-08-25):** official HH API is **unavailable**
for resume list on the current application/session (`GET /resumes/mine` = 403).
**Selected:** authenticated **browser session** as **READ-ONLY** transport for the
operator's own resume list only. Product/domain layers must consume a stable
HH-normalized resume-summary contract (not DOM details). This does **not** approve
browser apply, resume edits, negotiations scrape, arbitrary scraping, CAPTCHA
bypass, or auth/permission bypass — those need separate decisions.
Implementation of the browser resume list is **R1.3** (**COMPLETE**;
OWNER ACCEPTED 2026-08-26).

---

## 4. User Stories (PB-00)

### US-00.1 — Understand HH connection state

```text
Как оператор,
Я хочу видеть актуальное состояние подключения HeadHunter,
Чтобы знать, можно ли читать HH context и что делать, если нельзя.
```

**In scope:** session / login_ready / token readiness / clear recovery hints.  
**Non-scope:** resume list, apply, scoring.

### US-00.2 — See current HH account / profile

```text
Как оператор,
Я хочу видеть контекст своего HH account/profile,
Чтобы подтвердить, что Job Search смотрит на правильный аккаунт.
```

**In scope:** fetch + display account identity fields available from HH.  
**Non-scope:** editing HH profile.

### US-00.3 — List available HH resumes

```text
Как оператор,
Я хочу получить список доступных HH resumes,
Чтобы выбрать, с каким резюме работать дальше.
```

**In scope:** list contract + empty / blocked outcomes.  
**Non-scope:** editing resume content on HH.

### US-00.4 — Select active HH resume

```text
Как оператор,
Я хочу выбрать одно активное HH resume (или явно оставить выбор пустым),
Чтобы последующие шаги использовали известный resume context.
```

### US-00.5 — Restore active resume after restart

```text
Как оператор,
Я хочу, чтобы выбранное активное resume восстанавливалось после restart,
Чтобы не выбирать его заново каждый раз.
```

### US-00.6 — Explicit action-required states

```text
Как оператор,
Я хочу явно видеть not authorized / expired / CAPTCHA / permission denied,
Чтобы не путать внешний блок с «пустым списком» или молчаливым сбоем.
```

### US-01.1 — Minimal local linkage (minimal PB-01)

```text
Как оператор,
Я хочу связать активное HH resume с локальным CandidateProfile / ProfileVersion,
Чтобы R2 мог опираться на локальный candidate context, а не только на ephemeral HH id.
```

**In scope:** minimal Core model + link to `source=hh` + external resume id + restore.  
**Non-scope:** SearchProfile, scoring policy, resume history analytics, multi-provider.

---

## 5. TECH-US

### TECH-US-00.1 — HH client contract for profile + resumes

Stable HH-side read contract (CLI and/or internal API) for:

- connection status envelope
- account/profile fetch
- resume list fetch
- typed error codes: `not_authorized`, `expired`, `captcha_or_action_required`, `permission_denied`, `network_failure`

Builds on existing session/oauth/`AuthenticatedHhApi`; does not invent product UI.

### TECH-US-00.2 — Live access probe artifact

**Status: DONE (2026-08-25)** as a one-shot operator probe (not a unit-test /
CI network dependency). Recorded outcomes above. Re-run only when HH app
credentials/scope or token setup change.

### TECH-US-00.3 — Core minimal linkage schema + API

Introduce minimal CandidateProfile / ProfileVersion (names TBD at schema task)
with HH resume identity fields and active-link semantics. Versioned HTTP/JSON only.

### TECH-US-00.4 — Web HH context surface

Minimal R0-consistent panel/section for connection + profile + resumes + errors.
Prefer extending existing IA over a new Settings product.

---

## 6. DEBT-US (only real debt)

| ID | Debt | Why debt (not external) |
|---|---|---|
| **DEBT-US-00.1** | Product-facing HH connection absent despite implemented CLI session/auth | Operator cannot see R1 connection state in product UI |
| **DEBT-US-00.2** | `list_resumes_mine` exists only as metrics counter helper | Not a resume-list product capability |
| **DEBT-US-00.3** | ~~`/me` unproven~~ → **closed by probe**; product surface delivered in R1.2 (owner acceptance pending) | Was docs-ahead |
| **DEBT-US-00.4** | Live applications sync assumes `/negotiations` readable while API returns **403** | Confirmed live 2026-08-25; brittle happy path |

**Not DEBT-US:** HH API 403 scope itself; missing browser apply transport (separate track).

---

## 7. Acceptance Criteria by story

### US-00.1

1. Given HH session is not ready, when operator opens connection status, then state is explicit **not ready** with next action (e.g. open-login / confirm).
2. Given login_ready but access token missing/expired, then status shows **token action required**, not “connected”.
3. Given login_ready + valid token store, then status shows **ready for authenticated reads**.
4. Status never prints tokens/cookies.

### US-00.2

1. Given ready authenticated session and `/me` (or chosen substitute) succeeds, then operator sees account identity fields (at least stable id/name as available).
2. Given 401/expired, then profile is not shown as empty success — **action required**.
3. Given 403 permission limitation on profile endpoint, then **permission denied** is explicit.

### US-00.3

1. Given transport that can list resumes, then operator sees a list of resumes with external ids and display titles.
2. Given empty but authorized list, then UI/CLI shows **empty list**, not an error.
3. Given 403 on resume transport, then result is **permission denied / external limitation**, **never** silently empty success.
4. Given network failure, then failure is explicit and retry is operator-controlled (no silent loop).

### US-00.4

1. Operator can select exactly one active resume from the list.
2. Operator can clear selection to explicit **none**.
3. Selection is rejected if resume id is not in the last successful list (or revalidated).

### US-00.5

1. After process/container restart, previously selected active resume id is restored.
2. If restored id is no longer available, state is **stale selection** + action required (re-select), not silent fake success.

### US-00.6

1. 401 / expired → action required (re-auth), no silent retry storm.
2. CAPTCHA / action required → stop + explicit state; no bypass.
3. 403 scope → explicit external limitation.
4. These states are distinguishable in the operator-facing contract.

### US-01.1

1. Selecting active HH resume creates/updates local linkage: `source=hh`, external resume id, link to CandidateProfile/ProfileVersion.
2. Linkage survives restart.
3. Fresh install without selection has **no** automatic legacy/`legacy_job_search` candidate data.
4. Clearing active resume clears or marks linkage inactive without deleting unrelated Core history.

---

## 8. BDD / Gherkin (useful E2E only)

```gherkin
Feature: R1 HeadHunter context

  @us-00.1
  Scenario: Working session is visible as ready
    Given HH login is confirmed and an access token is stored
    When the operator requests HH connection status
    Then the status is ready for authenticated reads
    And no secrets are exposed

  @us-00.2
  Scenario: Account profile available when HH allows it
    Given HH connection status is ready
    And the account profile transport succeeds
    When the operator requests HH account context
    Then account identity is shown

  @us-00.3
  Scenario: Resume list available when HH allows it
    Given HH connection status is ready
    And the resume list transport succeeds
    When the operator requests the resume list
    Then available resumes are shown with external ids

  @us-00.3 @us-00.6
  Scenario: Permission denied is not an empty list
    Given HH connection status is ready
    And the resume list transport returns 403
    When the operator requests the resume list
    Then the result is permission denied
    And it is not presented as an empty successful list

  @us-00.4 @us-00.5
  Scenario: Active resume survives restart
    Given a resume list is available
    And the operator selected one active HH resume
    When the HH/Core services restart
    Then the same active resume id is restored

  @us-00.6
  Scenario: Expired session requires operator action
    Given the access token is expired or revoked
    When the operator requests HH account or resumes
    Then an expired/not-authorized action-required state is shown
    And the system does not silently retry in a loop

  @us-00.6
  Scenario: CAPTCHA or action-required stops automation
    Given HH returns a captcha or action-required condition on a guarded path
    When the operator-facing flow encounters it
    Then the flow stops with an explicit action-required state
    And no captcha bypass is attempted

  @us-01.1
  Scenario: Active resume links to local profile version
    Given an active HH resume is selected
    When local linkage is created
    Then Core stores source hh and the external resume id
    And the linkage is readable after restart
```

---

## 9. Minimal PB-01 data / API / UI proposals

### Data (Core) — proposed minimum

Introduce (exact names in schema task / ADR if needed):

- **CandidateProfile** — single-operator local candidate identity (UUID).
- **ProfileVersion** — versioned snapshot used as linkage target for R1 (and later scoring input).
  - Minimum fields: id, candidate_profile_id, created_at, optional label.
- **ActiveHhResumeLink** (or fields on ProfileVersion):
  - `source = "hh"`
  - `external_resume_id` (string)
  - optional cached `title`
  - `selected_at`
  - `status`: `active` | `cleared` | `stale`

Do **not** require SearchProfile. Do **not** reuse `Person` or `Application.resume_version` as the link.

### HH API / CLI — proposed minimum

- `session`/`auth` status already exist → add product envelope codes for R1 states.
- New: account/profile read command.
- New: resumes list command (distinct from metrics helper).
- New or Core-owned: get/set active resume (persistence location decided in R1.4/R1.5; prefer Core as domain SoT for linkage).

### Web UI — proposed minimum

One compact HH context surface (panel or light workspace addition) showing:

- connection state
- account/profile summary
- resume list + active marker
- action-required / error banner

Use R0 Calm Dense Productivity; no large Settings subsystem.

### Config / secrets

Document required env only (existing HH `.env.example` pattern). Never commit tokens, cookies, profiles, real `.env`.

---

## 10. Implementation Task order

| Task | Delivers | Depends on |
|---|---|---|
| **R1.1** | Operator-visible HH connection/session status (CLI + HTTP + Web) | **COMPLETE** (OWNER ACCEPTED 2026-08-25) |
| **R1.2** | HH account/profile read + display via official `GET /me` | **COMPLETE** (OWNER ACCEPTED 2026-08-26) |
| **R1.3** | Resume list via **authenticated browser read-only** transport (owner decision) | **COMPLETE · PUSHED** (OWNER ACCEPTED 2026-08-26) |
| **R1.4** | Active resume select + persistence (US-00.4 + US-00.5 restart) | **COMPLETE · PUSHED** (OWNER ACCEPTED 2026-08-26) |
| **R1.5** | Minimal Core CandidateProfile/ProfileVersion linkage | **COMPLETE · PUSHED** (OWNER ACCEPTED 2026-08-26) |
| **R1.6** | Unified recovery/action-required states across CLI+Web | **COMPLETE · PUSHED** (OWNER ACCEPTED 2026-08-26) |
| **R1.A** | Integrated R1 acceptance / Gate evidence | **TECHNICAL / INTEGRATED PASS** (2026-08-27) |

**R1.2 official API:** **YES** (`GET /me` = 200) — product transport for account context.  
**R1.3 official API:** **NO** (`GET /resumes/mine` = 403).
**R1.3 transport decision:** authenticated browser session, read-only own resumes
(**COMPLETE · PUSHED**).

**R1.4 SoT:** HH state file `active_resume.json` (selection); Core holds linkage (R1.5).
**R1.5 boundary:** identifier-only linkage (`external_resume_id` + optional `title`).
**Not** resume content. **Not** scoring-ready CandidateProfile.
Before **PB-03 Scoring**, **R2 / full PB-01** must add a local resume content
snapshot/version. Web «Локальная связь: активна» = acceptance/debug visibility.

**R1.6:** additive `recovery.{kind,operator_action}` on connection/account/resumes;
distinguishable reauth / captcha_or_action_required / external_limitation /
network_failure; no CAPTCHA bypass; bounded polls only. **PUSHED**.

**R1.A:** integrated evidence collected; **Gate R1 READY FOR OWNER DECISION**.  
Do **not** write Gate R1 CLOSED / ACCEPTED here.  
**Gate R1:** **OPEN**.

### R1.A — Gate R1 OWNER checklist (user-facing only)

1. Открой http://127.0.0.1:18080/
2. В шапке: HeadHunter **Подключено** и видно имя/аккаунт.
3. В блоке **«Резюме HH»** видны реальные названия твоих резюме.
4. Выбери рабочее резюме — оно явно active (✓ / выделение).
5. Reload страницы — выбор остаётся.
6. Нет ошибок вместо рабочего resume context.
7. По желанию: **«Сбросить выбор»** → выбрать снова.

Не нужно вручную симулировать все error states (они покрыты тестами).

Reply **ACCEPT** (закрыть Gate R1) или list remarks. Gate остаётся OPEN до ACCEPT.

### R1.6 OWNER ACCEPTANCE — ACCEPTED

**OWNER ACCEPTED** 2026-08-26. Happy-path Web check: connected + resume list intact;
login CTA intentionally hidden while authorized. Slice **COMPLETE · PUSHED**.

### R1.6 OWNER ACCEPTANCE checklist

Смысл среза: когда с HH что-то не так, на экране **понятно что именно**,
а не «пустой список резюме» и не бесконечная тихая перезагрузка.

Prerequisite: `make up` / `make dev`; страница http://127.0.0.1:18080/
(после деплоя R1.6 кода в HH+Web).

**Обязательно (happy path + «нужен вход»):**

1. Открой http://127.0.0.1:18080/
2. Если HH уже вошёл — в шапке «Подключено», в блоке «Резюме HH» видны
   названия резюме (как в R1.3/R1.4). Это ок: срез не ломает рабочий путь.
3. Нажми в блоке резюме что-то вроде **«Войти в HeadHunter»** / открой окно
   входа, **не** завершая вход до конца (или выйди из HH в окне входа и
   обнови страницу Job Search).
4. Ожидание: вместо списка резюме — явный текст вроде
   «Чтобы показать ваши резюме, войдите…» / «Сессия истекла…» и кнопка входа.
   **Не должно** выглядеть как «Пока нет резюме в аккаунте».

**Если само случится (не обязательно устраивать специально):**

5. HH показал CAPTCHA / «подтвердите, что вы человек» в окне входа —
   в Job Search должно быть видно, что нужно действие оператора / проверка,
   а не тихий успех и не пустой список.
6. HH отказал в доступе к резюме — текст про ограничение доступа HH,
   не «пока нет резюме».
7. Сеть/HH временно недоступны — явная ошибка; страница **не** крутит
   обновление списка без остановки десятки минут.

CLI/`recovery.kind` — **не** часть ручной приёмки (это для разработчика).

Reply **ACCEPT** or list defects. Slice is not COMPLETE until ACCEPT.
Local commits only until you ask to push.

### R1.5 OWNER ACCEPTANCE — ACCEPTED

**OWNER ACCEPTED** 2026-08-26. Observable: select active HH resume → Core
`candidate-context` linkage active; clear → cleared; survives reload.
Slice **COMPLETE · PUSHED**. Identifier-only (no resume body ingestion).

### R1.5 OWNER ACCEPTANCE checklist

Prerequisite: documented `make up` / `make dev` with Core migrated (`alembic` head includes
candidate-context). Browser HH session logged in; R1.4 select works.

1. Open http://127.0.0.1:18080/
2. In **«Резюме HH»** see your resume titles.
3. Select one resume as active (✓).
4. See **«Локальная связь: активна — …»** with that title (no curl).
5. Reload the page — active resume and local linkage remain.
6. **«Сбросить выбор»** — active cleared; linkage shows no active resume / cleared.
7. Select again — linkage becomes active again.

STOP until owner says `ACCEPT` / «принимаю».

Developer evidence: Core/HH/Web `make test` green; Core migration `20260826_08`;
`GET /api/v1/candidate-context`; HH select returns `core_linkage.ok`.

### R1.4 OWNER ACCEPTANCE — ACCEPTED

**OWNER ACCEPTED** 2026-08-26 (product review of active resume select on
http://127.0.0.1:18080/ «Резюме HH»). Slice **COMPLETE**.

### R1.4 OWNER ACCEPTANCE checklist

Prerequisite: stack via documented `make up` / `make dev`. Browser HH session
already logged in so «Резюме HH» shows your real titles (R1.3).

1. Open http://127.0.0.1:18080/
2. In **«Резюме HH»** see your real resume titles (not API/curl).
3. Click one resume title — it becomes **active** (✓ / stronger chip).
4. Reload the page — the same resume stays active.
5. Click another resume (if you have more than one) — only the new one is active.
6. Optional: **«Сбросить выбор»** — explicit none; prompt to select again.
7. If a previously selected resume disappeared from HH — see stale message and
   re-select (not a fake «still active» success).

STOP until owner says `ACCEPT` / «принимаю».

Developer evidence (not for owner): HH/Web `make test` green; live
`GET /api/v1/resumes` includes `selection` / `items[].active`;
`PUT /api/v1/resumes/active` selects/clears; invalid id → 409.

### R1.3 OWNER ACCEPTANCE — ACCEPTED

**OWNER ACCEPTED** 2026-08-26. Observable: http://127.0.0.1:18080/ strip
**«Резюме HH»** shows real resume title(s) via browser RO transport.

Delivered and accepted:
- HH browser RO scrape of own resumes (`resumes list` / `GET /api/v1/resumes`);
  official `GET /resumes/mine` remains 403.
- Product CTAs: «Войти в HeadHunter» (noVNC) → «Я вошёл — показать резюме»;
  auto-refresh when session becomes available.
- Clean titles (no bump/автоподнятие chrome); statuses for not logged in /
  blocked / unavailable without fake empty list.
- OAuth header «Подключено» / account identity remains R1.2 context (API),
  separate from browser resume session.

### R1.2 OWNER ACCEPTANCE checklist (re-acceptance)

Prerequisite: stack via **documented** `make up` (or `make dev`) — not a manual socat sidecar.

1. Confirm `docker compose ps` shows `hh-egress` when HH `.env` has a loopback HTTP proxy
   (or that `JOB_SEARCH_HH_HOST_PROXY_MODE=off` and direct egress works in your env).
2. Open `http://127.0.0.1:18080/` (this workspace `WEB_PORT=18080`).
3. Header: **HeadHunter** + **Подключено**.
4. Line **«Аккаунт: …»** with identity (`display_name`; tooltip may show `email`).
5. No raw JSON / tokens / resume list / «0 resumes».
6. Optional: `curl -sS http://127.0.0.1:8092/api/v1/account` → `status=available` (no PII in notes).
7. Resume list is **not** in R1.2.

STOP until owner says `ACCEPT` / «принимаю».

---

## 11. Gate R1

### A. Error-handling acceptance (required, not sufficient)

If an official API call returns 403, Job Search must show an **explicit external
permission limitation** (never a fake empty resume list). Same for 401/expired/
CAPTCHA. This is mandatory AC for US-00.6 / US-00.3.

### B. Product capability (required to CLOSE Gate R1)

A **supported** path must actually deliver:

- account/profile context;
- resume list;
- active resume select + restore;
- local CandidateProfile/ProfileVersion linkage.

**Official-API resume list (2026-08-25, re-confirmed 2026-08-27):** `/resumes/mine`
remains **403 EXTERNAL_BLOCKED**. Product resume list uses **browser read-only**
(R1.3 COMPLETE · PUSHED). Showing only the 403 state ≠ Gate CLOSED; supported
browser path + R1.1–R1.6 + R1.A evidence are now in place.

**R1.A (2026-08-27):** **TECHNICAL / INTEGRATED PASS**.  
**Gate R1:** **READY FOR OWNER DECISION · OPEN** (not CLOSED / not ACCEPTED).

Gate checklist (all must be true for owner to CLOSE Gate R1):

1. HH connection state is understandable to the operator.
2. With a working session, HH account/profile context is known **or** the blocking reason is explicit.
3. Resume list is available on a **supported** path (browser RO; not merely a documented 403).
4. Exactly one active working resume is selected **or** explicit none/cleared.
5. Active resume restores after restart (or stale+reselect is explicit).
6. Local CandidateProfile/ProfileVersion linkage exists for the active resume (identifier-only).
7. 401 / expired / CAPTCHA / 403 are presented explicitly; no silent retry loops; no captcha bypass.
8. External permission limitation is not masked as success.
9. Applicable tests green (`make test` workspace + HH/Core/Web gates used by the slice).

---

## 12. Non-scope reminder

Do not in R1 implementation:

- full PB-01 SearchProfile
- PB-02 / PB-03 / R2 scoring foundation
- browser apply as primary product path
- HH 403 bypass
- schema work unrelated to minimal linkage
