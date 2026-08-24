# R0 Acceptance

**Task:** T-UX-00.8 — functional regression + final visual review (+ IA correction)  
**Gate:** T-UX-00.9 — Gate R0 with product owner  
**Date:** 2026-08-22 (UTC+3)  
**Web SHA:** `86f37cb2647a49eababba0189ba8df24565b51bc`  
**Workspace SHA (Gate documentation baseline):** `4148599b19412d49aa5328ec9ddfd19306b7c491`

Normative: [`DESIGN.md`](../DESIGN.md). Screenshots: [`t-ux-00.8-ia5/`](r0/screenshots/t-ux-00.8-ia5/).

## Gate decision

**GATE R0: ACCEPTED WITH NON-BLOCKING DEBT**  
**Date:** 2026-08-22  
**PB-UX-00:** CLOSED  
**T-UX-00.8:** COMPLETE  
**T-UX-00.9:** COMPLETE  

Gate has **no blockers**. R0 is no longer current implementation work.

## Accepted state

- Calm Dense Productivity; primary R0 scheme: **dark**
- **Five** top-level workspaces: Vacancies, Journal, Metrics, People, Hypotheses
- Assessment / ScoringResult: **contextual to Vacancy** (not standalone workspace)
- Six dialogs (assessment record dialog removed from UI; Core API unchanged)
- Legacy `#assessments` hash → `#vacancies`
- Web `make test`: **37 passed**

Full scoring-in-vacancy flow (ranking, user decision) deferred to **R2 / PB-03–PB-04**.

## Scope checked (T-UX-00.8)

| Area | Result |
|---|---|
| Navigation | exactly **5** top-level links; `#assessments` → `#vacancies` | OK |
| Vacancies | list + OSINT detail + embedded assessment when data exists | OK |
| Journal … Hypotheses | unchanged flows | OK |
| Assessment API | POST/GET via Core gateway (integration + BDD) | OK |
| Standalone Assessments UI | removed | OK |
| System states | loading/empty/error/offline/notice (T-UX-00.7 baseline) | OK |

## Visual review

Screenshots: `docs/r0/screenshots/t-ux-00.8-ia5/` (01–10).

## Known non-blocking debt

May include (not Gate blockers):

- workspace cursor-rule test involving `12-no-choice-menus.mdc`;
- legacy naming (`panel-eyebrow`, metrics class naming);
- duplicate smoke/demo Core data;
- repository housekeeping / old untracked R0 artifacts.

Do not reopen R0 for these unless architecture revision reveals an actual blocker.

## Recommendation

**Gate R0 closed.** Next product slice: **R1 / PB-00** (HH connection and active resume).
