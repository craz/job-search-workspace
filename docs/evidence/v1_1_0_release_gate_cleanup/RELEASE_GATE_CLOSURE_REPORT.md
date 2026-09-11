# v1.1.0 RELEASE GATE CLOSURE REPORT

**When:** 2026-09-11 ~15:35 MSK  
**Path:** `/data/Projects/job_search_ref`  
**push=0** (no push / tag / publish)

## Verdict

**RELEASE GATES GREEN? YES**  
**READY TO PUBLISH v1.1.0? YES** (owner publish decision; this slice does not push)

**Functional product source behavior changed this cleanup? NO**  
(only format/lint/mypy mechanical edits already in prior cleanup commits; this re-verify added a Web **test assert** sync to existing cache-bust query.)

---

## 1. Exact previous red gates

| Gate | Was |
|---|---|
| Core `make format-check` / `make test` | RED (format + sqlite progress JSON) |
| HH `make format-check` / collect / `make test` | RED (format + BDD basename clash) |
| Web `make format-check` / `make test` | RED (format; later stale asset assert vs `r63`) |
| Scoring `make format-check` / `make test` | RED (format + product mypy) |
| Workspace `make test` / doctor | RED when web gitlink ≠ HEAD |

At start of this re-verify (post viewport ACCEPT, web at `165e233`): **only Web integration** failed — stale `?v=20260911-r61-refresh-btn` / `styles.css?v=…-r58` vs shipped `…-r63-score-viewport`. Format/lint already green on Core/HH/Web/Scoring.

## 2. Root causes

1. **Format:** uncommitted / unformatted Python across Core/HH/Web/Scoring after product commits.
2. **HH BDD clash:** pytest default import mode collided on shared basenames  
   `tests/bdd/test_apply_dry_run.py` ↔ `tests/unit/test_apply_dry_run.py` (and `test_apply_limited.py`).
3. **Web gate lag:** integration assert not updated when cache-bust moved to `r63-score-viewport`.
4. **Workspace doctor:** gitlink pin lag behind web HEAD after commits.

## 3. Formatting / lint fixes

Already landed in prior cleanup commits (mechanical only):

| Repo | Commit | Notes |
|---|---|---|
| Core | `424a635` | format + sqlite-safe progress JSON (portability) |
| HH | `4e63ab4` | format/lint + importlib |
| Web | `0874480` | format/lint (+ earlier asset assert) |
| Scoring | `67e13d6` | format/lint + product mypy greens |

This turn: **no further format/lint edits** (already green).

## 4. BDD clash fix

**Smallest fix:** `services/hh/pyproject.toml` addopts `+ --import-mode=importlib`.

**Proof (this turn):**

- Joint collect/run: `uv run pytest -q tests/unit tests/contract tests/bdd` → **245 passed**
- `make test`: format/lint/mypy + unit **215** + contract **17** + bdd **13**

## 5. ProfileLock status

**No mandatory release gate fails because of ProfileLock** (HH `-k 'profile_lock or ProfileLock'` → 5 passed, 240 deselected).

**Keep as known debt:** suitable/`resumes-list` race (`profile_locked`); integrated flow passed with wait. **Not redesigned.**

## 6. Full gate results per repo (re-run 2026-09-11)

| Repo | Command | Result |
|---|---|---|
| Core | `make test` | GREEN — format, lint, mypy; unit 126; integration 38; contract 9; bdd 18 |
| HH | `make test` + joint 245 | GREEN — format, lint, mypy; unit 215; contract 17; bdd 13 |
| Web | `make test` (incl. **js-syntax**, **js-smoke**) | GREEN — format, lint, mypy; js OK; unit 35; integration 55; contract 58; bdd 12; bootstrap-smoke OK |
| Scoring | `make test` (no calibration) | GREEN — format, lint, mypy; unit 593 (+1 skip); integration 8; contract 2; bdd 4 |
| Workspace | `make test` after pin | GREEN — unit + bdd (see post-pin run) |

## 7. Functional changes introduced?

**NO** (product scoring/policy/UI semantics unchanged in this cleanup).  
Web change this turn: **test-only** assert strings for cache-bust query already present in `index.html`.

## 8. Final HEAD manifest

| Component | HEAD |
|---|---|
| workspace | *(commit after pin + this report)* |
| core | `424a635d16cede1f62abc094b228a02e217a4c52` |
| hh | `4e63ab4d9a833d4413a58de494a918fcfba9f0a6` |
| web | `b1125964b88205e7d51a58b56b256a2b1651303b` |
| scoring | `67e13d6456e578046ca495fa67103ef105be9960` |
| osint | `123c00cd04e2c35084fe784b70c783ea13466f4f` (unchanged) |
| content | `05e9d7c637dfc37c4f848e1faa396a50b38f6b9e` (unchanged) |

## 9. Clean / dirty status

After workspace pin commit: all listed trees **clean**; no unrelated work staged.

## 10. Workspace pin consistency

`make doctor` expects web HEAD == gitlink. Pin updated to `b112596`. Doctor ERROR for web HEAD/gitlink mismatch resolved.

## 11. Commits (local, push=0)

| Repo | SHA | Subject |
|---|---|---|
| core | `424a635` | chore(core): release-gate format/lint + sqlite-safe progress JSON |
| hh | `4e63ab4` | chore(hh): release-gate format/lint + BDD basename collect fix |
| web | `165e233` | fix(web): keep viewport stable on manual «Оценить» (OWNER ACCEPTED product) |
| web | `b112596` | test(web): sync cache-bust asserts to r63-score-viewport |
| scoring | `67e13d6` | chore(scoring): release-gate format/lint + product mypy greens |
| workspace | *(this)* | chore: pin web b112596 + v1.1.0 release-gate closure report |

## 12. push=0

Confirmed: no `git push`, no tag, no publish.

## 13. Remaining known debt

- ProfileLock suitable race (observe-only; wait mitigates smoke).
- Scoring calibration package typing under mypy override (no expensive rewrite).
- Web js-syntax/js-smoke need Node on PATH (nvm on this machine).

## 14–15. Closure

| Question | Answer |
|---|---|
| RELEASE GATES GREEN? | **YES** |
| READY TO PUBLISH v1.1.0? | **YES** (owner must explicitly authorize push/tag) |

**STOP.**
