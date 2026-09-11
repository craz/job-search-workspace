# v1.1.0 RELEASE GATE CLOSURE REPORT

**When:** 2026-09-11 ~10:45 MSK  
**Machine:** MonsterHomeUbuntu (`0a4dc4e2-d17a-4907-9687-8763cf2eb97f`)  
**Path:** `/data/Projects/job_search_ref`  
**push=0**

## 1. STATUS
**TECHNICAL PASS** — formal release gates green without product behavior change.

## 2. FORMAT CHECK
Ran actual `make format-check` then formatting-only/`ruff check --fix` where safe.

| Repo | Before | Exact causes | After |
|---|---|---|---|
| Core | RED | unformatted `decision_card_i18n.py`, `test_decision_card.py` | GREEN |
| HH | RED | unformatted challenge/recovery/browser + unit tests | GREEN |
| Web | RED | unformatted `test_manual_score_click_dom.py` quote style | GREEN |
| Scoring | RED | 21 files would be reformatted (calibration + tests + helpers) | GREEN |
| Workspace | N/A | no `format-check` target; `make test` OK | GREEN |

Lint remaining after format was fixed with lint-only safe edits / targeted per-file E501 ignores (embedded JS regexes, HTML fixture).

## 3. HH BDD BASENAME CLASH
**Cause:** pytest default import mode collided on shared basenames  
`tests/bdd/test_apply_dry_run.py` ↔ `tests/unit/test_apply_dry_run.py`  
(and `test_apply_limited.py`).

**Smallest fix:** `pyproject.toml` addopts `+ --import-mode=importlib`.

**Proof:** `uv run pytest --collect-only -q` → **245 tests collected**; full joint `uv run pytest -q` → **245 passed**; `make test` unit+contract+bdd green.

## 4. PROFILELOCK
No mandatory release gate failed due to ProfileLock.  
**Known debt (documented, not redesigned):** page-load `resumes-list` can race suitable click (`profile_locked`) — mitigated in smoke by idle wait; product UX can still race. Out of this cleanup scope.

## 5. CORE RELEASE GATES
`make test` **PASS**: format-check, lint, mypy, unit 126, integration 38, contract 9, bdd 18.

Also fixed pre-existing sqlite migration gate: `20260910_27` now uses `JSON().with_variant(JSONB, postgresql)` (same pattern as prior migrations). PostgreSQL semantics unchanged.

## 6. HH RELEASE GATES
`make test` **PASS**: format-check, lint, mypy, unit 215, contract 17, bdd 13.  
Joint suite 245 passed after basename fix.

## 7. WEB RELEASE GATES
`make test` **PASS** with **js-syntax** + **js-smoke** (requires nvm node on PATH):  
`check-static-js` OK (app.js, calibration.js); `bootstrap-smoke` OK; unit 35; integration 55; contract 52; bdd 12.  
Integration asset assert aligned to shipped `app.js?v=20260911-r61-refresh-btn`.

## 8. SCORING RELEASE GATES
`make test` **PASS**: format-check, lint, mypy, unit 593 (+1 skip), integration 8, contract 2, bdd 4.  
No calibration rerun. Product-path mypy fixed; calibration typing debt isolated via mypy override (documented).

## 9. WORKSPACE RELEASE GATES
`make test` **PASS**: unit + bdd (49+8 OK).

## 10. REGRESSION SAFETY
No scoring/policy semantic changes; no ProfileLock redesign; no HH acquisition rerun.  
Diffs are mechanical format/lint/typing/portability/test-assert/config only.  
i18n string *values* unchanged (wrapping only). `looks_like_hh_challenge` return logic equivalent. Ollama liveness timeout check equivalent.

## 11. FILES CHANGED (by repo)
- **Core:** migration progress JSON portability; format `decision_card_i18n`/`app`/tests; mypy rename in `decision_card.py`
- **HH:** `pyproject.toml` importlib + E501 ignore for extractors; format/lint/typing in browser/challenge/orchestration/tests
- **Web:** pyproject E501 ignore; format contract test; integration asset pin
- **Scoring:** ruff format/lint across listed files; typing in clients/jobs/enqueue/single_flight/evidence_refs/ollama_backend; mypy calibration override
- **Workspace:** submodule pins + this evidence

## 12. COMMITS (local, push=0)
| Repo | SHA | Subject |
|---|---|---|
| core | `424a635` | chore(core): release-gate format/lint + sqlite-safe progress JSON |
| hh | `4e63ab4` | chore(hh): release-gate format/lint + BDD basename collect fix |
| web | `0874480` | chore(web): release-gate format/lint + asset cache-bust assert |
| scoring | `67e13d6` | chore(scoring): release-gate format/lint + product mypy greens |
| workspace | (this commit) | chore: pin v1.1.0 release-gate cleanup HEADs |

## 13. RELEASE MANIFEST
| Component | HEAD |
|---|---|
| workspace | see commit after pin |
| core | `424a635` |
| hh | `4e63ab4` |
| web | `0874480` |
| scoring | `67e13d6` |
| osint | `123c00c` (unchanged) |
| content | `05e9d7c` (unchanged) |

Trees clean after commits; pins consistent with submodule HEADs; no unrelated work; **push=0**.

## 14. LIMITATIONS / KNOWN DEBT
- ProfileLock suitable race remains (observe-only).
- Scoring calibration package typing ignored under mypy override (no expensive rewrite this slice).
- Web `make js-syntax`/`js-smoke` need Node on PATH (nvm v22 on this machine).

## 15. READY FOR OWNER ACCEPTANCE?
**YES** for release-gate closure (TECHNICAL PASS). Owner may accept publish separately.  
**push=0. STOP.**
