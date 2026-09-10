# Agent completion report contract

Portable reporting standard for **any** coding agent working in this repository
(Cursor, Codex, Cline, OpenCode, DevAI-backed clients, etc.). Cursor-specific
rules under `.cursor/rules/` implement the same lifecycle; they do not replace
this contract.

Canonical lifecycle states remain in `DEVELOPMENT_PROCESS.md` /
`.cursor/rules/10-development-workflow.mdc`:

`TECHNICAL PASS` → `READY FOR OWNER ACCEPTANCE` → `OWNER ACCEPTED` → `COMPLETE`

plus Web self-validation (`make js-syntax` / `make js-smoke`).

## When a completion report is required

After any **implementation**, **bugfix**, **acceptance prep**, or
**investigation that claims a status** (PASS / PARTIAL / FAIL).

## User prompt has priority

If the current user prompt contains explicit **`RETURN:`** and/or
**`Acceptance:`** (or equivalent checklist) sections, that text is the **exact
output contract** for the task:

1. Preserve the requested section headings / items.
2. Answer **every** requested item.
3. Keep YES/NO checklists as YES/NO (or `NOT VERIFIED` / `N/A` with reason).
4. Never silently drop a bullet because the answer is long or awkward.
5. A short summary may appear **first**; the full requested report must follow.

## No compression

Do **not** replace a required report with only phrases like:

- «всё сделано» / «готово»
- «make test green»
- «TECHNICAL PASS»
- «details above»
- «жду ACCEPT»

if the prompt asked for a detailed `RETURN` / Acceptance body.

## Default completion report (when RETURN is not specified)

Use this structure (adapt labels, keep substance):

1. **STATUS** — `TECHNICAL PASS` | `PARTIAL` | `NOT VERIFIED` | `FAIL`
2. **Cause / gap / RCA** — why the work was needed; for bugs: exact root cause
3. **What changed** — files / behavior (truthful, scoped)
4. **Evidence** — commands, outputs, logs, screenshots paths, URLs
5. **User-flow / runtime evidence** — required for UI/runtime tasks (real browser
   or real stack smoke of the changed flow). Unit/string-contract alone is not
   enough for user-visible Web changes.
6. **Tests / gates** — exact pass/fail/skip (include Web `js-syntax` / `js-smoke`
   when Web shipped JS changed)
7. **Commits** — per repo / submodule SHAs and subjects
8. **Push status** — default `push=0` unless owner waived
9. **Limitations / remaining blockers**
10. **Acceptance checklist** — YES/NO (or NOT VERIFIED) per item
11. **READY FOR OWNER ACCEPTANCE?** — YES/NO
12. **STOP** — do not start the next slice automatically

### Bugfix extras (mandatory)

1. Exact root cause  
2. Reproduction / evidence  
3. Fix  
4. Before / after behavior  
5. Regression tests  

### UI / runtime extras (mandatory)

- Real browser or real product runtime smoke of the **changed** flow  
- Not only unit / string / contract tests  

## PASS semantics

**TECHNICAL PASS** only if **all** are true:

- the requested task scope is done;
- required automated gates for that scope actually ran and passed
  (Web JS: `make js-syntax` + `make js-smoke` as part of `make test` when
  applicable);
- required runtime/browser evidence was obtained for UI/runtime work;
- every Acceptance item from the prompt was checked.

If anything required was not executed or not observed → **`PARTIAL`** or
**`NOT VERIFIED`**, never invent PASS.

**OWNER ACCEPT** / **OWNER ACCEPTED** is a **separate** owner action and must
not be inferred from TECHNICAL PASS.

**COMPLETE** (for user-facing product slices) = TECHNICAL PASS **and** OWNER
ACCEPTED (see `DEVELOPMENT_PROCESS.md`).

## STOP contract

After the completion report: **STOP**.

Do not auto-start the next slice. STOP does **not** mean “shorten the report”:
full report first, then STOP.

## Alignment

| Existing rule | How this contract fits |
|---|---|
| TECHNICAL PASS | Status in the report; requires real gates + evidence |
| Web self-validation | Part of required Web gates before PASS |
| READY FOR OWNER ACCEPTANCE | Explicit YES/NO + checklist in the report |
| OWNER ACCEPT | Separate; report may ask for it after STOP |
| STOP | After report; no next slice |

## Bad vs good (compressed example)

**Bad**

> make test green, commits…, TECHNICAL PASS

**Good (minimum substance)**

> STATUS: TECHNICAL PASS  
> RCA: …  
> Changes: …  
> Evidence: `make test` exit 0 (js-syntax OK, js-smoke OK, …)  
> Commits: web `abc…`, workspace `def…`  
> push=0  
> Acceptance: item1 YES / item2 YES  
> READY FOR OWNER ACCEPTANCE? YES  
> STOP.
