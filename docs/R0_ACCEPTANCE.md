# R0 Acceptance

**Task:** T-UX-00.8 — functional regression + final visual review (+ IA correction)  
**Date:** 2026-08-22 (UTC+3)  
**Web SHA:** `b65522d` + uncommitted IA5 patch (`?v=20260822-ia5`)  
**Workspace SHA:** `5afbcd6` + uncommitted docs/screenshots  
**Gate R0:** not closed (T-UX-00.9 with product owner)

Normative: [`DESIGN.md`](../DESIGN.md). Baselines: [`docs/r0/screenshots/t-ux-00.6-dark/`](r0/screenshots/t-ux-00.6-dark/), [`docs/r0/screenshots/t-ux-00.7/`](r0/screenshots/t-ux-00.7/). Review sets: [`t-ux-00.8-review2/`](r0/screenshots/t-ux-00.8-review2/), [`t-ux-00.8-ia5/`](r0/screenshots/t-ux-00.8-ia5/).

## Scope checked

- **Five** top-level sections: `#vacancies`, `#journal`, `#metrics`, `#people`, `#hypotheses`
- Assessment / ScoringResult: **not** a standalone workspace; contextual display in Vacancy rows (existing `/api/v1/assessments` client join)
- Six dialogs: vacancy, application, metric, person, hypothesis, hypothesis-close (assessment record dialog removed from UI; API unchanged)
- T-UX-00.7 system states on live Web + stub runtime
- Core online/offline signal and section error/recovery (stub)
- Legacy `#assessments` hash redirects to `#vacancies`

No product features beyond IA correction. No Scoring architecture changes. Full scoring-in-vacancy flow (ranking, decision) deferred to **R2 / PB-03–PB-04**.

## Product decision (IA correction)

Top-level **«Оценки»** removed from R0 navigation. Assessment / ScoringResult is a domain result tied to Vacancy, not an independent user workspace.

**R0 implementation:**

- Removed nav item, section view, section count, manual assessment dialog
- `loadVacancies()` fetches `/api/v1/assessments` in parallel and maps latest result per `vacancy_id`
- Vacancy row trailing: verdict badge + score; expand: reason / risk / action
- Core `/api/v1/assessments` GET/POST unchanged; existing data preserved

## Automated tests

| Suite | Result |
|---|---|
| Web `make test` | **37 passed** |
| Workspace `make test` | not re-run in IA5 pass |

## Functional regression

**Result: PASS**

| Area | Checks | Result |
|---|---|---|
| Navigation | exactly **5** top-level links; `#assessments` → `#vacancies` | OK |
| Vacancies | list + OSINT detail + **embedded assessment** when data exists | OK |
| Journal … Hypotheses | unchanged flows | OK |
| Assessment API | POST/GET via Core gateway (integration + BDD) | OK |
| Standalone Assessments UI | removed (no section, no nav, no record dialog) | OK |

## Review2 fixes (prior pass)

- Empty notice bar — fixed (`clearNotice`, guarded `showNotice`)
- Assessments screenshot artifact — clarified; data was always in renderer

## System states / accessibility

Prior review2 results stand. Notice hidden-by-default preserved.

## Visual review (IA5)

Screenshots: `docs/r0/screenshots/t-ux-00.8-ia5/`

| File | Content |
|---|---|
| `01-vacancies` … `05-hypotheses` | Five sections, no Assessments nav |
| `06-vacancy-assessment-context.png` | Vacancy row with score/verdict (live fixture) |
| `07-notice-success.png`, `08-no-notice.png` | Notice states |
| `09-error.png`, `10-offline.png` | Distinct error vs offline (stub) |

Removed obsolete `06-assessments-restored.png` expectation.

## Remaining issues

Non-blocking items from prior passes (invalid hash after in-session nav, dialog eyebrows, metrics class naming, workspace cursor-rule test, duplicate smoke rows) — unchanged.

## Recommendation

**READY FOR GATE R0**

R0 IA correction applied; Assessment API intact; five-section navigation verified. Product owner runs **T-UX-00.9** to close Gate R0.
