# Job Search Design System

**Product:** Job Search Web  
**Status:** normative for R0 / PB-UX-00 and later UI work  
**Authority:** overrides ad-hoc visual choices in Web static UI  
**Research basis:** [`docs/R0_DESIGN.md`](docs/R0_DESIGN.md), [`docs/R0_UI_AUDIT.md`](docs/R0_UI_AUDIT.md), [`docs/R0_DESIGN_REFERENCES.md`](docs/R0_DESIGN_REFERENCES.md)  
**Direction:** Calm Dense Productivity (Asana structure + Linear density + Attio record metadata + GitHub restrained surfaces)

This document is a **specification**, not an implementation. R0 code migration starts at T-UX-00.3+.

---

## Design goals

The interface must feel:

| Goal | Meaning |
|---|---|
| Calm | Neutrals dominate; color is semantic, not decorative |
| Dense | Dozens of vacancies scannable without scrolling past heroes |
| Functional | Every chrome element earns its space |
| Desktop productivity | Mouse + keyboard; app chrome, not landing page |
| Data-first | Objects and states read before brand voice |
| Low visual noise | No competing shadows, gradients, or nested frames |
| Clear hierarchy | One primary focus per view |

### Design rules (concrete)

1. **Working surface first.** First viewport shows app chrome + primary list/content, not a marketing slogan.
2. **One visual language.** Same button, badge, row, and dialog patterns in all six areas.
3. **List-first for collections.** Cards are the exception, not the default.
4. **Status is a badge + text**, never color alone.
5. **Elevation is rare.** Shadows only for overlays (dialog, popover), not for every panel.
6. **Whitespace is structural** (grouping), not empty hero padding.
7. **Existing product behavior stays.** Redesign does not invent R1+ flows or change domain contracts.

---

## Product UI model

### Current reality (must respect)

- Single UI route: `/`
- Six working areas on one document: Vacancies, Journal, Metrics, People, Hypotheses, Assessments
- Seven create/edit `<dialog>`s
- No global navigation / active section today

### Target model for R0

Keep **one route** and the **same six areas + dialogs**. Change structure, not product scope.

```text
┌──────────────────────────────────────────────────────────┐
│ App header: product name · connection/health · (optional)│
├────────────┬─────────────────────────────────────────────┤
│ Global nav │ Section header                              │
│            │ title · count · primary action              │
│ Vacancies  ├─────────────────────────────────────────────┤
│ Journal    │ Main content (list / dashboard / …)         │
│ Metrics    │                                             │
│ People     │                                             │
│ Hypotheses │                                             │
│ Assessments│                                             │
└────────────┴─────────────────────────────────────────────┘
         Dialogs overlay the shell when open
```

| Piece | Rule |
|---|---|
| **App shell** | Fixed header + persistent global nav + main |
| **Global navigation** | Six items = existing sections; exactly one **active** |
| **Current section** | Active nav style + matching section title in main |
| **Main content** | **One section visible at a time** (not a long stacked page) |
| **Page/section header** | Title, optional count, short context, actions |
| **Primary actions** | One primary CTA in section header (e.g. «Добавить вакансию») |
| **Secondary actions** | Ghost/secondary in header or row-level menus/buttons |

Deep links via hash (`#vacancies`, …) are allowed to select the active section without new backend routes.

**Out of R0 UI model:** new product modules, Board view implementation, command palette, multi-page router rewrite.

---

## Navigation

| Rule | Detail |
|---|---|
| Pattern | Persistent **left nav** (preferred) or compact **top tabs** if width is constrained; same six labels |
| Orientation | User always sees which section is active |
| Switching | Selecting a nav item shows that section in main; hides others |
| Long page | **Retire** endless stacked scroll as the primary model |
| Desktop | Nav always visible ≥ ~960px; labels readable |
| Connection | Core online/offline stays in **header**, not as a fake nav item |

Journal create may remain contextual (from Vacancy) — header primary CTA is not mandatory for every section, but placement rules stay consistent when a CTA exists.

---

## Layout

### Shell

- Header height compact (~48–56px)
- Nav width ~200–240px (collapsible icon+label later; R0 can be fixed)
- Main fills remaining width

### Content width

- Default main content: fluid up to **~1120–1280px**, then soft cap with side margin
- Dialogs: see Dialogs
- Do not full-bleed marketing bands

### Padding & section spacing

- Page/main padding: **16–24px**
- Section header → content: **12–16px**
- Between list rows: per Lists (tight)
- Avoid `clamp(4rem, 9vw, 8rem)` chapter gaps between unrelated stacks — sections are separate views

### Panels

- Use a **single surface** (page background + optional bordered content region)
- Metric summary: **metric cells in one panel** (grid/dividers), not cards-inside-cards

### Cards — when allowed

| Allowed | Not allowed |
|---|---|
| Empty/error state container (distinct styles) | Nested card inside card for OSINT/mirrors |
| Rare highlight of a single summary block | Default vacancy as large shadowed card grid |
| Dialog surface | Every entity type inventing its own chrome |

**Density:** prefer **list rows** for Vacancies, Journal, People, Hypotheses, Assessments collections. Metrics = dashboard panel + history list/bars.

---

## Typography

Small, sequential scale. One UI sans family (actually loaded in implementation). **No display serif hero** in the app shell.

| Role | Approx size | Weight | Use |
|---|---|---|---|
| Page / section title | 20–24px | 600–650 | Section header |
| Item title | 14–15px | 600 | Vacancy/person/hypothesis title in row |
| Body | 13–14px | 400 | Descriptions, reasons |
| Metadata | 12px | 400–500 | Source, dates, secondary fields |
| Labels | 12px | 500–600 | Form labels (sentence case, not screaming caps) |
| Secondary | 12–13px | 400 | Muted help, safety notes |
| Score (Assessment) | 20–28px | 650 | Prominent but not 4rem billboard |

**Implementation (T-UX-00.3):** `--font-family-ui` uses an honest system sans stack
(`ui-sans-serif, system-ui, …`) without declaring unloaded webfonts. Inter may be
added later via self-hosted files if product chooses; until then no fake `Inter`
in CSS.

Rules:

- Line-height ~1.35–1.5 for body; tighter for rows (~1.25)
- Avoid Georgia/editorial display inside working UI
- Uppercase micro-labels only for rare eyebrow/badge text, not all form labels

---

## Spacing

Compact scale (px): **4 · 8 · 12 · 16 · 24 · 32**

| Token idea | Value | Typical use |
|---|---|---|
| space-1 | 4 | Icon gaps, badge pad |
| space-2 | 8 | Inline control gaps |
| space-3 | 12 | Row internal padding-y start |
| space-4 | 16 | Panel padding, form gaps |
| space-5 | 24 | Section header padding, dialog pad |
| space-6 | 32 | Rare large separation |

Minimize one-off `0.72rem` / `0.9rem` magic; map to the scale in T-UX-00.3.

**Implementation (T-UX-00.3):** `--space-1` … `--space-6` = 4/8/12/16/24/32px in Web CSS.

---

## Colors

Semantic roles first. Implemented in Web as `--color-*` CSS variables (T-UX-00.3).

| Role | Intent | Token (Web CSS) |
|---|---|---|
| `bg` | App background — neutral light gray/off-white | `--color-bg` `#f4f5f7` |
| `surface` | Panels, dialogs, rows on hover slightly distinct | `--color-surface` `#ffffff` |
| `text` | Primary ink | `--color-text` `#141820` |
| `text-secondary` | Metadata, help | `--color-text-secondary` `#5c6574` |
| `border` | 1px separators and control borders | `--color-border` `#d8dde5` |
| `accent` | Brand/interactive accent — restrained cool blue | `--color-accent` `#2563eb` |
| `success` | Positive / online / completed | `--color-success` `#15803d` |
| `warning` | Risk, needs attention, unverified OSINT | `--color-warning` `#b45309` |
| `danger` | Error, destructive, offline-critical | `--color-danger` `#b91c1c` |
| `info` | Neutral informational highlight | `--color-info` `#0369a1` |
| `muted` | Disabled/chrome quiet fills | `--color-muted` `#e8ebf0` |

Legacy component aliases (`--ink`, `--paper`, …) remain temporarily and map to
the roles above until T-UX-00.4+ migration.

Rules:

- Accent ≠ success ≠ danger  
- Charts/scores may use accent or a dedicated score tone — **not** the same token as form error  
- Dark mode is **out of R0**

---

## Borders / radius / shadows

| Property | Rule |
|---|---|
| Borders | **1px** `border` color; no 2px ink frames as default |
| Radius | Small: **4–8px** controls/badges; dialogs ~8px |
| Shadows | **Only** overlays (dialog backdrop + dialog elevation). No hard `8px 8px 0` offset on every card |
| Dividers | Prefer row separators / 1px lines over boxed nests |

---

## Buttons / actions

Exactly **four** variants. Kill the current five+ parallel styles.

| Variant | Use |
|---|---|
| **Primary** | One main CTA per section header or dialog confirm |
| **Secondary** | Alternative solid/outline for important non-primary |
| **Ghost** | Cancel, tertiary, in-row quiet actions |
| **Destructive** | Delete/discard/irreversible (rare in current Web) |

States:

| State | Behavior |
|---|---|
| Hover | Slightly stronger bg/border; no large translate/jump |
| Focus | Visible focus ring (accent or dedicated); never remove |
| Disabled | Reduced opacity + `not-allowed`; not look like ready primary |
| Processing | Disabled + progress cue (spinner or «…» label); keep width stable |

Row actions (apply, research, confirm) use **secondary/ghost**, not a second «primary» look. Hypothesis «close» in-row = secondary, not header primary styling.

---

## Forms

| Element | Rule |
|---|---|
| Input / select / textarea | Same height rhythm (~32–36px inputs); 1px border; surface fill |
| Labels | Above field; sentence case; associated via `label` |
| Help | Secondary text under field |
| Error | `danger` text + optional border; `role="alert"` where already used |
| Dialog forms | 1–2 columns max; full-width for long text |
| Safety notes | Info/muted callout with left border or icon — not acid marketing bar |

Keep native `<dialog>` pattern acceptable for R0.

---

## Status / badges

Critical for Job Search.

### Pattern

```text
[●] Label
```

- Compact pill/chip: padding from spacing scale  
- **Color + text label** (and optional icon)  
- Same component for vacancy status, person status, hypothesis active/closed, assessment verdict  

### Semantic mapping (visual only; domain enums unchanged)

| Kind | Badge intent |
|---|---|
| Neutral / new | muted or info |
| In progress / reviewing / researching | info or accent soft |
| Positive / applied / replied / apply-verdict | success |
| Caution / maybe / unverified OSINT | warning |
| Negative / rejected / skip / offline | danger or muted+danger text |
| Terminal closed (hypothesis done) | muted |

Do **not** invent new domain statuses in R0 — only render existing ones consistently.

Future hiring stages / scoring states must reuse this badge system, not new one-off colors.

---

## Lists / tables

Default collection UI.

| Rule | Detail |
|---|---|
| Row density | Comfortable-compact: ~40–48px row height desktop |
| Primary info | Left: title (vacancy/person/…) |
| Secondary | Under or beside: company, next action, metric |
| Metadata | Right or trailing: source, dates, badges, score |
| Actions | Trailing ghost/secondary; selects stay compact |
| Hover | Subtle surface change |
| Selected | Optional stronger border/bg when multi-select appears later; R0 may skip selection |
| Separators | 1px row borders or zebra-quiet; not heavy cards |
| Empty | See System states — dedicated empty, not dashed error twin |

Vacancies must support **scanning dozens of rows**: title + status badge + company + key meta in one row; OSINT/mirrors as **expandable secondary block or detail region**, not nested card stacks inside every row by default.

---

## Dialogs

| Aspect | Rule |
|---|---|
| Width | `min(32–40rem, 100% - 2rem)` for standard forms; wider only if needed |
| Header | Title + ghost close; optional context line |
| Body | Form fields; no extra decorative panels |
| Actions | Right-aligned: ghost Cancel + primary Submit; destructive on left or separate if ever needed |
| Destructive confirm | Explicit copy; destructive button variant |
| Focus | Focus trap while open; restore focus to opener on close |
| Keyboard | Escape closes; Enter submits when safe |

---

## System states

Must be **visually distinct**.

| State | Pattern |
|---|---|
| **Loading** | Inline skeleton or spinner **in main content**; `aria-busy`; actions that depend on data not looking ready |
| **Empty** | Calm illustration-optional; title «Нет …»; one primary CTA when applicable; **no danger color** |
| **Error** | Danger accent; clear message; retry if applicable; **not** the same dashed empty card |
| **Success / notice** | Transient notice in **shell** (header-adjacent or sticky top of main), visible from any section |
| **Offline / degraded** | Header signal + optional banner; vacancy load failure uses Error pattern |

---

## Domain mapping

Visual presentation of **existing** objects (no domain changes).

### Vacancy

- **Primary:** list row — title, company, status badge, source  
- **Secondary:** link, description excerpt  
- **Actions:** status control, record application, research/mirrors (secondary)  
- **OSINT:** expandable/secondary region with provenance; confirm = secondary/primary-in-context carefully labeled  

### Application / Journal

- Dense list row: date · vacancy title · next action · resume meta  
- Status text if present; no fake «sent to employer» chrome  

### Metric

- Header CTA «Записать день»  
- Latest snapshot: one panel with metric cells (grid)  
- History: compact rows + bar — not nested summary cards inside shadowed cards  

### Person

- List/row preferred: name, role badge, company, contact status badge  
- Notes as secondary line; profile link ghost  

### Hypothesis

- Row: title, active/closed badge, sample/metric meta  
- Close action = secondary in row; result text when closed  

### Assessment

- Row or compact panel: vacancy title, **score**, verdict badge, model meta  
- Detail: reason → risk → action hierarchy (see AI)  

---

## AI / scoring presentation

For existing Assessment only:

| Element | Rule |
|---|---|
| Score | Visually prominent (larger weight/size) but secondary to vacancy identity in lists |
| Verdict | Semantic badge (`apply` / `maybe` / `skip`) |
| Explanation | Body text; first paragraph = reason |
| Risk / gaps | Warning-styled secondary block or labeled section — not same color as score |
| Action | Clear labeled next step |
| Processing / error | Reuse system Loading/Error; do not imply live model run if Web only stores normalized results |

No Scoring architecture redesign here.

---

## Accessibility / interaction

- Visible `:focus-visible` on all controls  
- Dialogs keyboard-operable; skip link retained/adapted to main  
- Contrast: text/badge text meets readable contrast on soft badge fills  
- `prefers-reduced-motion`: no obligatory motion; disable spinners animation when reduced  
- **No color-only semantics** (badge always has text)  

---

## Responsive scope

R0 is **desktop-first**.

| Viewport | Behavior |
|---|---|
| ≥ ~1100px | Full shell: sidebar + main |
| ~700–1100px | Narrower nav or top tabs; lists remain |
| < ~700px | Accept stacked header/nav; forms single column; **not** a polished mobile product |

Do not spend R0 on a separate mobile design system.

---

## Do / Don't

### DO

- Dense list rows for vacancies and journal  
- Semantic status badges with labels  
- One typography/spacing hierarchy  
- Restrained surfaces and 1px borders  
- One primary CTA per view  
- Distinct empty vs error  
- Shell notice visible across sections  

### DON'T

- Nested cards everywhere  
- Giant marketing hero inside the working app  
- Arbitrary hard offset shadows  
- Decorative gradients as chrome  
- Unrelated button styles per feature  
- Excessive empty space between sections  
- Acid/coral decorative accents as status substitutes  
- Scream-all-caps form labels as default  

---

## Control screens

Use the audit set from [`docs/R0_UI_AUDIT.md`](docs/R0_UI_AUDIT.md) §14 for before/after review in T-UX-00.3–00.8.

| Control | After redesign must show |
|---|---|
| First viewport | Shell + nav + Vacancies header + list rows (populated) |
| Vacancy + OSINT | Row/detail with secondary evidence; no nested card hell; multiple action variants correct |
| Applications list | Dense journal rows |
| Metrics | Panel cells + history without nested card stack |
| Create dialog | Header/body/actions per Dialogs |
| Empty section | Calm empty (e.g. People) |
| Error + offline | Distinct error + header degraded signal |
| Notice success/error | Shell-level notice |

---

## Implementation boundary

| In later R0 tasks | Not in DESIGN.md / T-UX-00.2 |
|---|---|
| Tokens in CSS variables | Editing `styles.css` now |
| Shell/nav markup | Editing `index.html` / `app.js` now |
| Primitive classes | New frontend framework |
| Migration of sections | Domain/API changes |

**Next engineering task:** T-UX-00.3 — design tokens + page shell (code), guided by this document.
