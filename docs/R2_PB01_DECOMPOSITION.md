# R2.1 / PB-01 slice — local ResumeVersion (decomposition)

**Status:** R2.1 DECOMPOSITION **OWNER ACCEPTED** (2026-08-27);  
**R2.1.1:** **OWNER ACCEPTED · COMPLETE · PUSHED** (Core ResumeVersion storage)  
**R2.1.2:** **READY FOR OWNER ACCEPTANCE** (HH read-only resume detail extract)  
**R2.1.3+:** **NOT STARTED**  
**Gate R1:** **CLOSED**  
**Canonical product SoT:** Google Drive doc **Job Search** (tabs Product Backlog, Roadmap, R2)

This document owns the accepted US / TECH-US / EXT / slices for **R2.1 only**.
Full R2 Gate remains after R2.1–R2.7. Do not treat R2.1 as Gate R2 CLOSED.

---

## 1. Product goal

R1 already provides:

```text
active HH resume
  → identifier-only local linkage
  → CandidateProfile / ProfileVersion (r1-default)
```

R2.1 adds a **local immutable version of the actual resume content**:

```text
active HH resume
  → manual read-only content acquisition (browser)
  → local immutable ResumeVersion / snapshot
  → CandidateProfile / ProfileVersion (unchanged r1-default)
```

Future **PB-03 Scoring** must be able to use that specific `ResumeVersion`
without re-reading HeadHunter.

---

## 2. Owner decisions (accepted 2026-08-27)

1. **Sync = MANUAL ONLY.** Selecting an active HH resume does **not** fetch content.
   Operator action: «Обновить» / «Синхронизировать содержание».

2. **First-time selected resume:** if no `ResumeVersion` exists for that
   `external_resume_id`, state = **content not synced**. Never create a fake/empty
   ResumeVersion.

3. **Previously synced resume (return):** when switching back to an HH resume that
   already has a local `ResumeVersion`:
   - latest local `ResumeVersion` is the **current local copy**;
   - show `captured_at` / synced timestamp;
   - offer «Обновить»;
   - history is retained;
   - **no** mandatory HH fetch on switch alone.

4. **Snapshot fields (allowlist, all optional by availability):**
   title / desired position, about / summary, skills, experience, education,
   languages, salary, location, employment/preferences, and other **confirmed**
   scoring-relevant fields from the HH owner page.

   **Never store:** phone, email, contacts, cookies, tokens, auth/session data.
   Extractor is **allowlist-oriented**, not “scrape whole DOM then filter”.

5. **Representation:** schema-versioned **normalized structured JSON / JSONB**.
   PDF / raw HTML are **not** required for R2.1 MVP.

6. **API:** ordinary `candidate-context` exposes ResumeVersion **metadata only**
   (`resume_version_id`, `external_resume_id`, `captured_at`, sync/content state).
   Full snapshot body = **separate explicit read endpoint**.

7. **ProfileVersion:** keep existing `label=r1-default` in R2.1.
   No SearchProfile / profile-versioning redesign.

8. **Active ResumeVersion:** **no** mandatory separate
   `active_resume_version_pointer` table.

   **Preferred minimal model:**

   ```text
   active HH linkage (ActiveHhResumeLink)
     + latest ResumeVersion for that external_resume_id
     = current local ResumeVersion
   ```

   See §4 for invariant check. Introduce a pointer/sync-state table **only** if
   implementation later proves an invariant cannot be satisfied without it.

---

## 3. Invariants

1. `ResumeVersion` holds factual resume content sufficient for future scoring.
2. `ResumeVersion` is **immutable**. HH content change → new row; old rows kept.
3. Re-sync with identical canonical content → **no** new `ResumeVersion`
   (hash / normalized representation).
4. Current local ResumeVersion is known when content has been synced for the
   active `external_resume_id`.
5. Provenance: `source=hh`, `external_resume_id`, `captured_at`, link to
   `ProfileVersion` / CandidateProfile, schema/transport metadata as needed.
6. PDF is optional; structured JSON is the required processable copy.

---

## 4. Active ResumeVersion without a pointer table

**Rule:** given `ActiveHhResumeLink.status=active` and non-null
`external_resume_id`, current local copy =

```text
ResumeVersion
  WHERE profile_version_id = <operator r1-default>
    AND source = 'hh'
    AND external_resume_id = link.external_resume_id
  ORDER BY captured_at DESC
  LIMIT 1
```

If no such row → **content not synced**.

| Scenario | Behaviour without pointer table |
|---|---|
| **A. First sync** | INSERT first immutable row; current = that row |
| **B. Unchanged sync** | No INSERT; current still latest; refresh UX from same `captured_at` (or show “already up to date”) |
| **C. Changed sync** | INSERT new row; current = new latest; old retained |
| **D. Switch resume** | Linkage updates; current = latest for **new** id, or not synced |
| **E. Return to previous** | Linkage to prior id; current = latest for that id; offer Update; no auto-fetch |
| **F. Clear** | Linkage cleared → no current; history retained |
| **G. HH unavailable** | Sync fails with recovery envelope; no fake row; if prior latest exists it remains current local copy |
| **H. Stale / deleted on HH** | Linkage `stale`; latest for that id still available as possibly outdated local copy |

**Persisted last-failure sync state** is **not** required for accepted MVP UX
(failed sync is returned by the sync action + R1.6 recovery). If a later slice
needs durable “last sync error across reload”, add the **minimal** field/table
then — not preemptively.

**Verdict:** separate pointer SoT **not required** for accepted R2.1 invariants.

---

## 5. Proposed data model (Core)

```text
resume_versions  (immutable)
  id
  profile_version_id  → profile_versions
  source              ('hh')
  external_resume_id
  schema_version      (int)
  content_hash        (SHA-256 of canonical JSON)
  content             (JSONB, normalized snapshot)
  captured_at
  transport           ('browser_readonly')
  extractor_version   (optional string)
```

Keep existing:

```text
candidate_profiles / profile_versions (r1-default)
active_hh_resume_links  (identifier-only SoT for which HH resume is active)
```

**Do not** stuff resume body into `ProfileVersion` or `ActiveHhResumeLink`.

### Snapshot schema (v1, all fields optional by availability)

```json
{
  "schema_version": 1,
  "title": "...",
  "desired_position": "...",
  "about": "...",
  "skills": ["..."],
  "experience": [{"company": "...", "position": "...", "period": "...", "description": "..."}],
  "education": [{"institution": "...", "degree": "...", "year": "..."}],
  "languages": [{"name": "...", "level": "..."}],
  "salary": {"text": "..."},
  "location": "...",
  "employment_preferences": {"text": "..."}
}
```

Deny: phone, email, contacts, cookies, tokens.

### Change detection

1. Extract allowlisted fields → normalize (stable key order, trim, drop empties).
2. `content_hash = SHA256(canonical_utf8_json)`.
3. Compare to latest row for same `(profile_version_id, source, external_resume_id)`.
4. Equal → no INSERT; unequal → INSERT new immutable row.

---

## 6. Acquisition flow

```text
Operator selects active HH resume (R1.4/R1.5) — no content fetch
        ↓
Operator presses «Обновить» / sync content
        ↓
HH browser RO: open own /resume/{id} via existing Chromium profile
        ↓
Allowlist extract → normalized JSON envelope + recovery
        ↓
Core: hash compare → insert or skip → return metadata
        ↓
Web: human sync state (not debug linkage ids)
```

**Transport constraint:** official `GET /resumes/mine` remains **403 EXTERNAL_BLOCKED**.
Browser RO only; no CAPTCHA/auth bypass; no apply/edit/negotiations.

---

## 7. Minimal UX (extend «Резюме HH»)

Not permanent product UI: «Локальная связь: активна», ProfileVersion ids, hashes.

| State | Operator-visible meaning |
|---|---|
| Active + never synced | Рабочее резюме выбрано · Содержание ещё не синхронизировано · [Обновить] |
| Active + synced | Рабочее резюме «…» · Содержание синхронизировано · &lt;timestamp&gt; · [Обновить] |
| Return to prior synced | Same as synced using latest local copy · [Обновить] |
| Recovery / unavailable | Explicit R1.6-style message · no fake empty CV |
| Stale HH selection | Local copy may be outdated · re-select / update as applicable |

---

## 8. Product US

| ID | Purpose | Acceptance (summary) | Repos |
|---|---|---|---|
| **US-01.2** | Manual sync of resume content into local ResumeVersion | Given active HH resume + ready session, when operator syncs, then Core stores immutable content snapshot with provenance | HH, Core, Web |
| **US-01.3** | Human-readable sync/content state | Operator sees synced / not synced / recovery without curl | Web, Core |
| **US-01.4** | History + dedup | Unchanged → no new version; changed → new version; old kept | Core, HH |
| **US-01.5** | Current local ResumeVersion known | Metadata on candidate-context; body via dedicated read | Core, Web |

---

## 9. TECH-US

| ID | Purpose | Repos |
|---|---|---|
| **TECH-US-01.1** | `resume_versions` schema + immutability + hash | Core |
| **TECH-US-01.2** | Canonical normalization + content_hash | Core |
| **TECH-US-01.3** | HH browser allowlist detail extractor + recovery | HH |
| **TECH-US-01.4** | Manual sync orchestration HH → Core | HH, Core |
| **TECH-US-01.5** | candidate-context metadata + separate snapshot read API | Core, Web |

---

## 10. External constraints / debt

| ID | Note |
|---|---|
| **EXT-01** | `/resumes/mine` = 403 EXTERNAL_BLOCKED → browser RO only |
| **EXT-02** | HH DOM fragility on owner resume page → extractor_version + fixtures |
| **EXT-03** | Contacts visible on owner page → hard denylist (never store) |

---

## 11. BDD (useful)

```gherkin
Scenario: First select does not create ResumeVersion
  Given operator selects an HH resume that was never synced
  Then no ResumeVersion exists for that external_resume_id
  And UI shows content not synced

Scenario: Manual sync creates first ResumeVersion
  Given active HH resume without local content
  When operator runs sync content
  Then exactly one ResumeVersion exists for that external_resume_id
  And candidate-context metadata references it

Scenario: Unchanged sync does not create a new version
  Given synced ResumeVersion v1
  When operator syncs again and HH content is unchanged
  Then ResumeVersion count remains 1
  And current metadata still points at v1

Scenario: Changed content creates a new immutable version
  Given synced ResumeVersion v1
  When HH content changes and operator syncs
  Then v1 still exists
  And a new ResumeVersion is current

Scenario: Return to previously synced resume without HH fetch
  Given ResumeVersion exists for resume A
  And operator switched to resume B then back to A
  Then current local copy is latest ResumeVersion for A
  And no automatic HH content fetch was required for the switch
```

---

## 12. Internal slices (implementation later)

| Slice | Product meaning | Status |
|---|---|---|
| **R2.1.1** | Core stores immutable ResumeVersion | **OWNER ACCEPTED · COMPLETE · PUSHED** |
| **R2.1.2** | HH read-only extracts resume content | **READY FOR OWNER ACCEPTANCE** |
| **R2.1.3** | First end-to-end manual sync | **NOT STARTED** |
| **R2.1.4** | Version / dedup behaviour | **NOT STARTED** |
| **R2.1.5** | Human-readable Web state | **NOT STARTED** |

Do **not** start R2.1.3 until owner ACCEPTs R2.1.2.

---

## 13. Acceptance target (R2.1 complete)

> У Job Search есть локальная неизменяемая версия фактического содержания
> выбранного рабочего резюме, и продукт знает, какая именно версия сейчас
> является текущей локальной копией.

Must hold: history preserved; unchanged sync does not proliferate versions;
changed content creates a new version; UI is human language; snapshot is
usable for future PB-03; sync is manual-only.

---

## 14. Non-scope (R2.1)

- vacancy search / ingestion / normalization / dedupe (R2.2+)
- SearchProfile full UI
- scoring / Ollama / embeddings / SCORING_SERVICE_FOUNDATION (R2.3+)
- vacancy ranking / user vacancy decision
- applications / OSINT
- auto-sync on select
- PDF/raw HTML as required artifacts
- ProfileVersion redesign / multi-label profiles
- separate active-pointer table “just in case”

---

## 15. Repo impact (future implementation only)

| Repo | Later work |
|---|---|
| Core | migration, models, hash/dedup, metadata + snapshot APIs |
| HH | allowlist detail extractor, manual sync command/route |
| Web | sync CTA + human status; proxy |
| Scoring | **unchanged in R2.1** |
| Workspace | this decomposition + IMPLEMENTATION_PLAN alignment |

---

## 16. Relation to full R2 sequence (canonical)

| Phase | Focus |
|---|---|
| **R2.1** | Local ResumeVersion content snapshot (this doc) |
| **R2.2** | Search context + HH vacancy ingestion / normalization / dedupe |
| **R2.3** | SCORING_SERVICE_FOUNDATION |
| **R2.4** | Mass score/verdict in Vacancy + list prioritization |
| **R2.5** | Detailed scoring in Vacancy context |
| **R2.6** | Explicit user decision |
| **R2.7** | Basic PB-11 metrics slice |
| **Gate R2** | After R2.1–R2.7 product evidence + owner Gate decision |
