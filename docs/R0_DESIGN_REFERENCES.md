# R0 Design References — T-UX-00.2

**Product:** Job Search  
**Roadmap stage:** R0  
**Task:** T-UX-00.2 — visual direction  
**Status:** complete (2026-08-21)  
**Inputs:** [`R0_DESIGN.md`](R0_DESIGN.md), [`R0_UI_AUDIT.md`](R0_UI_AUDIT.md), public product UI knowledge

> Research notes. Нормативная спецификация — корневой [`DESIGN.md`](../DESIGN.md).  
> Не копируем branding/pixel sizes. Сравниваем принципы применительно к текущему Web
> (один `/`, шесть секций, dialogs, vacancy-first).

## 1. Products reviewed

| Product | Role in comparison |
|---|---|
| **Asana** | Primary structural reference (required) |
| **Linear** | Density, issue-list scanning, restrained chrome |
| **Attio** | CRM-like records, status + metadata density |
| **GitHub** | Familiar eng-tool surfaces, thin borders, lists |
| **Airtable** | Grid/metadata extreme — contrast, mostly «what not to copy wholesale» |
| **Notion** | Block canvas — contrast for why Job Search is not a doc tool |
| **Sentry / PostHog** | Ops dashboards — metrics/state panels without marketing hero |

## 2. Per-product notes

### Asana

**Полезно для Job Search**

| Area | Takeaway |
|---|---|
| Navigation | Stable left/top product nav; always clear «where am I» |
| List / table | List-first tasks; row = primary object; Board as alternate view of same entity |
| Density | High without clutter; whitespace is structural, not decorative empty hero |
| Status | Compact status chips; color + label |
| Metadata | Pills/fields along the row (assignee, due, custom) |
| Detail | Task opens as focused detail without losing project context |
| Dialogs / forms | Modal for create; inline edits for light changes |
| System states | Empty project / loading lists are distinct from chrome |

**Не переносить**

- Coral / brand illustration language  
- Mobile/iOS-specific layouts as R0 source of truth  
- Full Asana IA (portfolios, goals, workload)  
- Pixel-perfect component sizes  

### Linear

**Полезно**

| Area | Takeaway |
|---|---|
| Navigation | Compact sidebar; one active workspace view |
| List | Extremely scannable issue rows; title left, metadata right |
| Density | 13px-ish UI; tight row height; minimal chrome |
| Status | Semantic status + priority without loud fills |
| Metadata | Icons + short text; progressive disclosure |
| Detail | Side panel / issue page; list stays available |
| Dialogs | Command palette exists — **out of R0 scope**; keep native dialogs for create |
| System states | Quiet empty; clear error toasts |

**Не переносить**

- Keyboard-only as requirement for MVP  
- Cmd+K as primary nav for six sections (visible nav first)  
- Dark-first brand identity as mandatory  

### Attio

**Полезно**

| Area | Takeaway |
|---|---|
| Navigation | CRM sections as first-class destinations |
| List / table | Record tables with filters/saved views (views later; pattern = rows + fields) |
| Density | Many attributes per row without card nesting |
| Status | Pipeline/stage badges as primary scan cue |
| Metadata | Field cells, not nested cards |
| Detail | Record focus with related objects |
| Forms | Structured property editing |

**Не переносить**

- Full CRM customization surface in R0  
- Spreadsheet-like editable grid as default vacancy UX  

### GitHub

**Полезно**

| Area | Takeaway |
|---|---|
| Navigation | Top + contextual secondary; active state obvious |
| List | Issues/PRs: dense rows, labels, status dots + text |
| Surfaces | Near-flat; 1px borders; shadow almost only on overlays |
| Status | Labels + state text (open/closed) — color not sole cue |
| Dialogs | Modest modals; predictable action footer |
| System states | Clear empty repos / failed loads in content area |

**Не переносить**

- Primer-specific tokens wholesale  
- Marketplace/marketing landing patterns inside app  

### Airtable

**Полезно**

- Grid thinking for metrics history and multi-field objects  
- Field-type clarity (number vs text vs status)

**Не переносить**

- Spreadsheet as the whole product metaphor  
- Heavy cell chrome and rainbow field colors by default  

### Notion

**Полезно**

- Calm neutrals; content hierarchy  

**Не переносить**

- Block/page canvas as primary job-search workspace  
- Soft marketing emptiness; weak list density for dozens of vacancies  

### Sentry / PostHog (brief)

**Полезно**

- Metrics as compact panels + charts without nested card stacks  
- Error/offline as explicit operational states  
- Data-first headers (title + filters/actions), not slogans  

**Не переносить**

- Full observability IA  
- Alert fatigue aesthetics (too many severity colors at once)  

## 3. Asana vs others (for Job Search)

| Criterion | Asana | Better elsewhere for JS | Decision |
|---|---|---|---|
| List-first object model | Strong | Linear tighter rows | **Asana model + Linear density** |
| Global nav / active section | Strong | Linear/GitHub equally clear | **Asana-like stable nav** |
| Metadata along row | Strong | Attio stronger for many fields | **Asana pills + Attio field discipline** |
| Status semantics | Strong | GitHub label+text a11y | **Semantic badge + text** |
| Surfaces / borders | Calm | GitHub thinnest / least decorative | **GitHub-like restrained surfaces** |
| Alternate views (List/Board) | Strong | — | **Keep as future-ready principle** |
| Brand / color | Coral | Linear/GitHub neutrals | **Reject coral; own neutral + semantic** |
| Marketing hero in-app | Occasional onboarding | Ops tools never | **Reject current Web masthead** |
| Nested cards | Rare in lists | Linear avoids | **Reject current vacancy card nests** |

## 4. Synthesis — one direction (not a collage)

**Chosen direction name:** Calm Dense Productivity

Одно согласованное направление:

> Desktop productivity shell с list-first рабочей поверхностью, стабильной навигацией
> по существующим шести областям, компактными semantic statuses, тонкими borders и
> нейтральными surfaces. Визуальный слой подчиняется сканированию вакансий и их
> состояния; AI/OSINT/metrics вписываются как metadata и secondary panels, а не как
> отдельные «дизайны».

### Берём у Asana

- List-first + готовность к multiple views одного объекта  
- Stable global navigation + clear current place  
- Compact status + metadata along the primary row  
- Clear page hierarchy (title → tools → content)  
- Calm, non-decorative working surfaces  

### Лучше взять у других

| From | What |
|---|---|
| Linear | Row density, quiet chrome, scannable primary/secondary text split |
| Attio | Record/CRM treatment of contacts & pipeline-ish statuses |
| GitHub | 1px borders, labels+text, overlay-only elevation |
| Sentry/PostHog | Metrics/state panels without marketing; explicit degraded/error |

### Уникально для Job Search

- Vacancy as primary object (не «task» и не «issue» дословно)  
- Assessment score + reason/risk/action hierarchy (AI explainability)  
- OSINT provenance as secondary evidence (unverified vs confirmed) — без вложенных card hell  
- Safety notes for non-sending apply / research (уже есть в продукте)  
- Local funnel + journal semantics (Web не отправляет работодателю)  

### Сознательно отвергнуто

- Current neo-brutalist acid/Georgia marketing masthead  
- Coral Asana branding  
- Notion doc-canvas as home  
- Airtable spreadsheet as default vacancy UI  
- Linear Cmd+K as R0 navigation substitute  
- Decorative gradients / hard offset shadows everywhere  
- Five unrelated button styles  

## 5. Implication for current Web (audit facts)

| Audit fact | Direction response |
|---|---|
| One `/` + six sections | Keep single route in R0; introduce shell + section nav (pane switch or equivalent), not six new product features |
| No active section | Nav item = section; active required |
| Long scroll page | Target: one primary section in main at a time |
| Marketing masthead | Replace with compact app header |
| Many button styles | Four variants only (see DESIGN.md) |
| No status badges | Introduce semantic badge pattern |
| Nested cards | Lists/rows default; cards rare |
| Empty ≈ error | Distinct system states |
| Existing CSS variables | Evolve into semantic tokens in T-UX-00.3 — not in this task |

## 6. Next

Норматив: [`../DESIGN.md`](../DESIGN.md).  
Implementation tokens/shell: **T-UX-00.3** (не начат здесь).
