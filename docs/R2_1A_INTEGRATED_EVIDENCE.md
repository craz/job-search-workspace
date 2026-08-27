# R2.1.A — Integrated acceptance / Gate evidence

**Status:** **TECHNICAL / INTEGRATED PASS** (2026-08-27)  
**R2.1:** **READY FOR OWNER DECISION** (not auto-COMPLETE)  
**R2.2:** **NOT STARTED**  
**Docs push:** **NOT pushed** (local only until owner decision)

Baselines after OWNER ACCEPTED R2.1.5 push:

| Repo | SHA | Remote |
|---|---|---|
| Web | `9abe407` | `origin/main` |
| Workspace | `42b5330` (+ this evidence commit) | `42b5330` was `origin/main` before R2.1.A docs |
| Core | `aa81914` | `origin/main` |
| HH | `737ac9d` | `origin/main` |

---

## 1. Normal startup

- `make up` — hh/core healthy; HH egress `hh.ru` reachable (302 via proxy).
- Web UI: `http://127.0.0.1:18080/`.

## 2. Integrated Web product flow (live)

Fixture (operator account, single HH resume):

- Active resume id: `f3e5e5f7ff0f50d3e50039ed1f4436664d7338`
- Title: **Project Manager / Руководитель IT-проектов**
- ResumeVersion: `c39fa10d-1ba2-4bd7-978d-4256987163d4`
- `captured_at`: `2026-08-27T11:56:19Z`

| Step | Result |
|---|---|
| 1. HH connection/account | `connected`; account available |
| 2. Working resume visible | Title shown as active |
| 3. Synced strip | «Содержание синхронизировано» + human timestamp + **Обновить** |
| 4. Reload | Active resume + synced metadata persist |
| 5. Manual **Обновить** | Browser RO + Core ingest; result **unchanged**; notice «Локальная копия уже актуальна.»; `resume_versions` count **1** |
| 6. After sync | Synced UI; no UUID/hash/ProfileVersion debug UX |
| 7. Clear active | Panel hidden; Core `content_state=none`; historical GET `/resume-versions/{id}` → **200**; count still **1** |
| 8. Unsynced other resume | **Not live-tested** — only one HH resume in list. Deterministic Core unit/integration/BDD cover `not_synced` + no cross-resume snapshot (see §4). No artificial HH state created. |
| 9. Return to synced | Latest local version appears immediately; count still **1** (no auto HH fetch creating versions); **Обновить** available |
| 10. Recovery | Automated HH/Core/Web suites green; HH guards skip Core on extract failure (no fake ResumeVersion) |

## 3. Data / invariants

| Invariant | Evidence |
|---|---|
| ResumeVersion immutable | Live: clear/return keeps same id; R2.1.4 fixture history (v1 preserved when v2 created) |
| Lookup scope `profile_version_id + source + external_resume_id` | Specs + Core history tests; no pointer table |
| Same content → no duplicate | Live sync **unchanged**, count=1; Core `test_unchanged_ingest_does_not_duplicate` |
| Changed content → new version + old preserved | Deterministic Core/BDD (no real HH edit) |
| PII absent in snapshot | Live full body: no phone/email keys/patterns; allowlisted keys only |
| candidate-context metadata only | Live: `CTX_HAS_BODY=False`; metadata fields only |
| Full body = explicit endpoint | `GET /api/v1/resume-versions/{id}` |

## 4. Point 8 — not_synced (deterministic only)

Live HH list size = **1**. Covered by existing automated evidence, including:

- `services/core/tests/unit/test_resume_version_history.py`
- `services/core/tests/integration/test_resume_version_history_api.py`
- `services/core/tests/bdd/test_resume_version_history.py`

## 5. Technical gates (R2.1.A run)

| Suite | Result |
|---|---|
| Core `make test` | format/lint/mypy + unit 33 + integration 22 + contract 8 + bdd 17 — **PASS** |
| HH `make test` | format/lint/mypy + unit 98 + contract 12 + bdd 13 — **PASS** |
| Web `make test` | format/lint/mypy + unit 5 + integration 29 + contract 2 + bdd 10 — **PASS** |
| Workspace `make test` | unit + bdd — **PASS** |
| Migration head | `20260827_09 (head)` == current |

## 6. Defects

None found in integrated flow. No production code changes in R2.1.A.

## 7. Final framing

```text
R2.1.1 COMPLETE · PUSHED
R2.1.2 COMPLETE · PUSHED
R2.1.3 COMPLETE · PUSHED
R2.1.4 COMPLETE · PUSHED
R2.1.5 COMPLETE · PUSHED

R2.1.A = TECHNICAL / INTEGRATED PASS
R2.1 = READY FOR OWNER DECISION
R2.2 = NOT STARTED
```
