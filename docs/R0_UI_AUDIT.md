# R0 UI Audit — T-UX-00.1

**Product:** Job Search  
**Roadmap stage:** R0  
**Task:** T-UX-00.1 — UI audit текущего Web  
**Status:** complete (from repository code, 2026-08-21)  
**Web submodule HEAD:** `d6d3bd1`  
**Workspace HEAD at audit:** `a64b487`

> Описание только реально найденного состояния Web.
> Отдельных клиентских routes кроме `/` нет: шесть рабочих секций живут на одной странице.

Execution-spec: [`docs/R0_DESIGN.md`](R0_DESIGN.md).  
Структура: [`docs/R0_UI_AUDIT_TEMPLATE.md`](R0_UI_AUDIT_TEMPLATE.md).

## 1. Executive summary

- Пользовательский UI — **одна SPA-страница** `GET /` (`index.html` + `app.js` + `styles.css`): секции Вакансии, Журнал откликов, Дневные метрики, Люди, Гипотезы, Оценки + 7 `<dialog>`-форм.
- Визуально Web **согласован внутри одной editorial/neo-brutalist темы** (cream paper, acid accent, hard ink borders, offset shadows, Georgia display), но это **не** целевой B2B/productivity density из R0/Asana-гипотезы: крупный marketing hero, низкая плотность карточек, нет глобальной навигации.
- Главные системные проблемы для R0: нет page shell / global nav / active section; **5+ независимых button-реализаций**; статусы — текст/`select`, не badges; empty/error через общий `stateCard`, loading — только статический HTML-loader (после reload JS не рисует spinner); вся разметка карточек — string templates в одном `app.js`.
- Уже можно развивать: CSS variables (`:root`), паттерн toolbar + section + `stateCard` / `showNotice`, dialog/form-grid, `escapeHtml`, тестовые stubs в `tests/support.py`, BDD HTTP facade.
- Блокирует R0 как foundation: отсутствие navigation + page shell и разрозненные interactive primitives; не блокирует как функциональность — board уже работает через Core/OSINT HTTP.

## 2. Frontend stack

| Area | Reality in repo |
|---|---|
| Framework | Нет SPA-framework. Vanilla HTML/CSS/JS |
| Server | FastAPI (`job_search_web/app.py`) отдаёт `index.html`, static `/assets/*`, same-origin `/api/v1/*` |
| Router | Нет client router. Единственный UI route: `/` |
| Styling | Один файл `static/styles.css`; CSS custom properties; без preprocessor / Tailwind |
| UI libraries | Нет |
| Icon library | Нет (символ `×`, стрелки `↗` в тексте) |
| Fonts | `Inter` в `font-family` **без** `@font-face` / CDN — фактически system stack; display: `Georgia, serif` |
| State / data | Imperative DOM + `fetch`; module-level arrays `knownVacancies`, `osintReports`, `mirrorReports` |
| Test stack | `pytest` unit / integration / contract; `pytest-bdd` + Gherkin `tests/features/vacancy_board.feature` — **HTTP facade**, не browser DOM |
| BDD / E2E | BDD есть; **browser E2E / Playwright / screenshot harness в Web-репозитории нет** (smoke упоминается в AGENTS/README как ручной/compose) |
| Build / dev | `make bootstrap`, `make dev`, `make test`; Compose + optional `WEB_LIVE_RELOAD=1` revision poll in `app.js` |

## 3. Screens / routes inventory

Клиентских path-routes нет. Ниже — **логические экраны** (якоря секций на `/`).

| Route | Screen (section) | Purpose | Key actions | Layout | States | R0 priority |
|---|---|---|---|---|---|---|
| `/` `#vacancies` | Вакансии (01) | Доска воронки | Add vacancy; status select; apply; OSINT research/mirrors/confirm; open URL | masthead → toolbar → card grid | loading (HTML), empty, error, populated (+ nested research) | **P0** |
| `/` `#applications` | Журнал (02) | Локальные факты откликов | нет create в toolbar (create из карточки вакансии) | toolbar + list rows | loading, empty, error, populated | **P0** |
| `/` `#metrics` | Дневные метрики (03) | Снимки темпа | Записать день | toolbar + 2-col dashboard | loading, empty, error, populated | **P1** |
| `/` `#people` | Люди (04) | Подтверждённые контакты | Add person; status select | toolbar + card grid | loading, empty, error, populated | **P0** |
| `/` `#hypotheses` | Гипотезы (05) | Эксперименты | New; close with result | toolbar + row cards | loading, empty, error, populated | **P1** |
| `/` `#assessments` | Оценки (06) | Нормализованные scores | Записать оценку | toolbar + card grid | loading, empty, error, populated | **P1** |
| `/` dialogs | 7 modal forms | Create/update flows | submit / cancel / close | `<dialog>` + form-grid | form-error; disabled submit (частично) | **P0** (как pattern) |

### 3.1 `/` — Вакансии

- **Назначение:** list/create vacancies, funnel status, local apply fact, OSINT people/mirrors.
- **Components (DOM classes):** `.vacancy-grid`, `.vacancy-card`, `.card-meta`, `.research-*`, `.confirm-button`, `.research-button`, `.application-button`, status `<select>`.
- **Loading:** initial `#loading-state` + `.loader` in HTML; `aria-busy` toggled in `loadVacancies`.
- **Empty:** `stateCard(..., "Воронка пока пуста", ...)`.
- **Error:** `stateCard` + signal offline.
- **Populated:** cards with nested research blocks.
- **Working scenarios:** list/create/status; application from card; OSINT research/confirm/mirrors (specs + BDD HTTP).

### 3.2 Журнал откликов

- Rows `.application-card` (date | title/next | resume).
- Empty/error via `stateCard`; no section-level primary create.

### 3.3 Метрики

- `.metric-latest` + nested `.metric-summary-card`; `.metric-history` bars.
- Latest panel has `box-shadow`; history panel does not (asymmetric).

### 3.4 Люди / Гипотезы / Оценки

- People: card + status select (зеркало vacancy pattern).
- Hypotheses: row layout; **close** uses `.primary-button` внутри карточки (тот же класс, что toolbar CTA).
- Assessments: large `.assessment-score`; verdict only as meta text.

### 3.5 Dialogs (общий pattern)

| Dialog id | Opens from |
|---|---|
| `#vacancy-dialog` | `#open-form` |
| `#application-dialog` | `[data-apply]` on vacancy |
| `#metric-dialog` | `#open-metric-form` |
| `#person-dialog` | `#open-person-form` |
| `#hypothesis-dialog` | `#open-hypothesis-form` |
| `#hypothesis-close-dialog` | `[data-close-hypothesis]` |
| `#assessment-dialog` | `#open-assessment-form` |

Структура: `.dialog-head` + `.form-grid` + `.form-error` + `.dialog-actions` (`.text-button` + `.primary-button`). Часть форм имеет `.safety-note`.

## 4. Navigation audit

### Global navigation

- **Где:** отсутствует. Есть только `.skip-link` → `#vacancies` и scroll по `main`.
- **Как выглядит:** marketing `.masthead` (eyebrow, huge `h1`, lede, Core `.signal`) — не nav.
- **Active state:** нет (нет nav items).
- **Повторное использование:** n/a.
- **Проблемы:** нельзя понять «текущий раздел» без scroll position; US-UX-00.2 BDD (active section) сегодня **невыполним** без новой nav.

### Local navigation

- Tabs / breadcrumbs / secondary nav: **нет**.
- Context actions: per-section toolbar CTA или in-card buttons; журнал без CTA в toolbar.

### Найденные проблемы

- [x] unclear active section — секций 6, nav нет
- [x] inconsistent placement — create application только в vacancy card; hypothesis close = primary-button in-card; research = outline; apply = filled ink
- [x] conflicting primary actions — `.primary-button` и в toolbar, и в hypothesis row
- [ ] duplicated patterns — нет двух разных global nav (их ноль)
- [x] другое: section anchors существуют (`id`), но нет in-page nav links на них

## 5. Layout audit

Inventory:

| Element | Implementation |
|---|---|
| Page shell | Нет общего shell-компонента; `body > header.masthead + main + dialogs` |
| Header | `.masthead` full-bleed hero |
| Sidebar | Нет |
| Main | `main` с clamp padding; секции подряд |
| Max-width | Контент без единого `max-width` container; `h1` max 12ch; dialog `min(44rem, …)` |
| Grids | `auto-fill` cards (19/18/22rem); application 3-col; metrics 1.2fr/0.8fr; hypothesis 2fr/0.7fr; form 2-col |
| Cards / panels | Heavy 2px ink border + often `box-shadow: 8px 8px 0` |
| Drawers | Нет; только `<dialog>` |

### Повторяющиеся patterns

| Pattern | Files | Reusable now? | Problem |
|---|---|---|---|
| Section toolbar (`section-number` + `h2` + CTA) | `index.html`, `styles.css` | Yes (markup copy) | Дублируется 6× вручную; journal CTA slot = note |
| Entity card + meta + footer | `app.js` templates | Pattern only | Разные min-heights / shadows / grids |
| `stateCard` dashed panel | `app.js` + `.state-card` | Yes (JS helper) | Loading ≠ same helper |
| Dialog chrome | 7× HTML | Markup copy | Нет shared template/component |

### Конфликты

- Masthead padding `clamp(2rem, 6vw, 6rem)` vs `main` `clamp(2rem, 5vw, 5rem) … 6rem` — разные вертикальные ритмы.
- Vacancy/person/assessment cards: shadow; application/hypothesis list cards: border only (кроме metric-latest).
- Nested surfaces: `.research-person` и `.metric-summary-card` внутри уже bordered cards → визуальный «card-in-card».
- Vacancy card `min-height: 15rem` + research blocks → очень высокие карточки, низкая плотность относительно list-first цели R0.

## 6. Typography audit

| Use | Current values | Locations | Problem |
|---|---|---|---|
| Body family | Inter (unloaded) → system-ui stack | `:root` | Заявленный Inter фактически не грузится |
| Display / headings | Georgia serif | `h1`, `h2`, card `h3`, scores | Marketing display vs productivity body |
| Page title | `clamp(3rem, 8vw, 7.5rem)`, lh `.87` | `.masthead h1` | Доминирует над рабочей областью |
| Section title | `clamp(2rem, 4vw, 3.8rem)` | `h2` | Крупно для 6 секций на одной странице |
| Card title | ~1.45–1.75rem Georgia | cards | OK внутри темы; не tokenized |
| Eyebrow / meta | `.72rem`, weight 750–800, tracking `.1–.16em`, uppercase | `.eyebrow`, `.section-number`, `.card-meta` | Повторяется, но без token |
| Body / muted | inherited / `--muted` | `.description`, notes | |
| Labels | `.78rem`, weight 800, uppercase | `label` | |
| Assessment score | `4rem` Georgia rust | `.assessment-score` | Единственный «hero number» |
| Weights | 400, 700, 750, 800, 850 | CSS | 750/850 зависят от font; нестандартная шкала |

## 7. Spacing audit

| Value / pattern | Locations | Consistent? | Comment |
|---|---|---|---|
| `1.5rem` | card padding, many gaps | Mostly | De-facto base |
| `1rem` / `.75rem` / `.7rem` | research, forms, history | Mixed | Magic steps |
| `2.5rem` | `.toolbar` margin-bottom | Section only | |
| `clamp(4rem, 9vw, 8rem)` | `*-toolbar` margin-top | Between sections 02–06 | Крупные «главы»; секция 01 без этого top |
| `clamp` page pads | masthead / main | Divergent | |
| Form grid gap `1rem`, margin `2rem 0` | dialogs | Yes among dialogs | |
| Row heights | application / metric-history | Ad-hoc | Нет единой row token |
| Button pads | `.9rem 1.2rem` vs `.7rem` vs `.45rem .7rem` | No | Три плотности CTA |

## 8. Colors / surfaces audit

| Purpose | Current value/pattern | Locations | Problem |
|---|---|---|---|
| Page bg | `--paper: #f2f0e8` | `body` | Warm cream editorial |
| Surface | `--surface: #fbfaf5` | cards, dialog | |
| Ink | `--ink: #16211c` | text, borders | |
| Accent | `--acid: #d8ff57` | masthead band, primary btn, notice, signal online | Decorative + success notice |
| Danger / emphasis | `--rust: #bc4d2f` | em, score, bars, loader, form-error, offline | Один цвет = error + chart + score |
| Muted | `--muted: #696e68` | secondary text | |
| Line | `--line: #c8c5b8` | dividers | |
| Shadow | `--shadow: 8px 8px 0 var(--ink)` | cards/dialog | Hard offset, not soft elevation |
| Notice error bg | `#ffd2c5` hardcoded | `.notice.error` | Вне tokens |
| Skip-link fg | `white` hardcoded | `.skip-link` | Вне tokens |
| Semantic status palette | отсутствует | statuses as labels/select | Нет success/warn/info tokens |

## 9. Components inventory

### Buttons

| Implementation | Locations | Reusable? | Variants | Problem |
|---|---|---|---|---|
| `.primary-button` | toolbars, dialog submit, hypothesis close | CSS class | default / `:disabled` opacity | Used for both page CTA and in-card action |
| `.application-button` | vacancy card | CSS class | filled ink | Duplicate of confirm visual language |
| `.confirm-button` | OSINT propose | CSS class | smaller filled ink | Third filled style |
| `.research-button` | OSINT actions | CSS class | outline | Fourth style |
| `.text-button` | dialog cancel | CSS class | transparent | |
| `.icon-button` | dialog close × | CSS class | large glyph | |

→ **Candidate:** one button primitive with variants `primary | secondary | ghost | danger`.

### Form controls

- `input`, `textarea`, `select` — shared CSS; select on cards `max-width: 9rem`.
- Checkbox/radio: нет.
- Labels: uppercase grid labels in dialogs; `sr-only` on in-card selects.
- → reusable pattern, not component module.

### Status / badges

- Нет badge-компонента. Status = text in `.card-meta` and/or `<select>`.
- OSINT: `.research-status` text «В Core»; heading «не проверено / подтверждено».
- Assessment verdict: meta span only (no color mapping).
- → **candidate** status/badge primitive.

### Cards / surfaces

- `.vacancy-card`, `.person-card`, `.assessment-card`, `.application-card`, `.hypothesis-card`, `.metric-latest`, `.metric-history`, `.state-card`, `.research-person`, `.metric-summary-card`.
- Mix of reusable CSS recipes and one-off grids.
- → candidate: `surface` + `list-row` + `entity-card`.

### Tables / lists

- Нет `<table>`. Lists: CSS grids (applications, hypotheses, metric history).
- Density: list rows denser than vacancy cards; still padded ~1.25–1.5rem.

### Dialogs / drawers

- Native `<dialog>` ×7; shared classes; no drawer.
- Reusable CSS; markup duplicated.

### Notifications

- `#notice.notice` / `.notice.error` via `showNotice` (4.5s auto-hide).
- Single global slot under first toolbar — ok for MVP; not toast stack.

### Loading / empty / error

| Kind | Implementation | Note |
|---|---|---|
| Loading | HTML `.loader` + copy per section | After first paint, reloads don't re-inject spinner |
| Empty / error | `stateCard()` dashed `.state-card` | Shared helper; titles differ |
| Inline research empty | `.research-empty` paragraphs | Different from section empty |

## 10. System states

| State | Existing pattern | Screens | Consistent? | Gap |
|---|---|---|---|---|
| Loading | `.loader` in initial HTML; `aria-busy` | All 6 sections | Partial | No JS loading template; busy without spinner on refresh |
| Empty | `stateCard` | All 6 | Yes among sections | Research empties differ |
| Error | `stateCard` + optional offline signal; form `.form-error`; notice.error | Sections / forms / global | Three channels | Same dashed card for empty and error |
| Success / confirmation | `showNotice` acid banner | After mutations | Yes | Notice sits under vacancies toolbar only — below-fold sections less visible |
| Disabled / processing | `disabled` + opacity on primary/research/confirm; select disabled during PATCH; button text «Ищем…» / «Подтверждаем…» | Forms, OSINT, status | Partial | Hypothesis/assessment submit не всегда disable button; disabled styled as faded primary, not distinct processing |

## 11. Concrete visual problems

| Problem | Screen / file | Why it hurts | Severity |
|---|---|---|---|
| Нет global navigation и active section | `/` `index.html` | Нельзя выполнить US-UX-00.2; ориентация только scroll | **High** |
| Masthead hero `h1` до 7.5rem занимает first viewport | `.masthead` / `styles.css` | Рабочая доска ниже fold; конфликтует с density-целью R0 | **High** |
| Шесть секций на одной странице без локальной nav | `index.html` `main` | Длинный scroll; primary actions размазаны | **High** |
| ≥5 button CSS implementations | `styles.css` + vacancy/hypothesis cards | Одинаковые действия выглядят по-разному; foundation для R1+ отсутствует | **High** |
| Status без единой badge/semantics; `--rust` = error + score + chart | cards / assessments / metrics | Статусы не сканируются; цвет не семантичен | **Medium** |
| Nested cards (research-person, metric-summary внутри bordered panels) | `vacancyCard`, `metricsView` | Шум, ниже density | **Medium** |
| Asymmetric card chrome (shadow vs no-shadow across entity types) | vacancy/person vs application/hypothesis | Сущности одного продукта выглядят разным «весом» | **Medium** |
| Empty и error — один `.state-card` dashed | `stateCard()` | Сложно отличить «нет данных» от сбоя без чтения текста | **Medium** |
| Loading spinner только в статическом HTML | `index.html` vs later `load*` | Повторная загрузка секции без единого loading pattern | **Medium** |
| `#notice` привязан под секцией 01 | `index.html` | Успех/ошибка действий в секциях 03–06 легко пропустить | **Medium** |
| Inter declared but not loaded | `styles.css` `:root` | Непредсказуемый fallback по ОС | **Low** |
| Hardcoded `#ffd2c5` / `white` вне tokens | `.notice.error`, `.skip-link` | Ломает будущую token migration | **Low** |
| Journal toolbar без primary CTA (в отличие от 01,03–06) | `#applications` toolbar | Непоследовательная модель «добавить» | **Low** |
| Hypothesis in-card `.primary-button` vs toolbar `.primary-button` | `hypothesisCard` | Primary action hierarchy размыта | **Medium** |

## 12. Technical debt discovered

| ID | Location | Problem | Why it affects R0 | Blocking? |
|---|---|---|---|---|
| TD-WEB-01 | `static/app.js` (~689 lines) | Весь UI: string HTML templates + listeners в одном файле | Миграция на primitives/shell потребует разрезать rendering; риск регрессий | Non-blocking (structure) |
| TD-WEB-02 | `static/index.html` | 6 toolbars + 7 dialogs скопированы вручную | Дубли markup усложняют единый shell/nav | Non-blocking |
| TD-WEB-03 | No client routes / nav | Product docs говорят «dashboards», UI — одна лента | R0 navigation US требует новой структуры поверх текущего | **Blocking for US-UX-00.2** |
| TD-WEB-04 | Tests HTTP-only | Нет browser visual/DOM harness | Gate visual review (TECH-US-UX-00.6) пока только ручной | Non-blocking for redesign start; blocking for automated visual gate |
| TD-WEB-05 | Font stack claims Inter without files | Typography foundation лжива | Tokens/typography в T-UX-00.3 должны выбрать реальный font load | Non-blocking |
| TD-WEB-06 | Cache-bust query `?v=20260820-mirrors` + optional live reload | Два механизма свежести assets | Не мешает visual language; путаница при review screenshots | Non-blocking |

DEBT-US не создавались.

## 13. Existing reusable foundation

Сохранить и развивать:

- **CSS variables** `:root` (`--ink`, `--paper`, `--surface`, `--line`, `--acid`, `--rust`, `--muted`, `--shadow`) — зачаток tokens.
- **Section rhythm:** `.toolbar` + `.section-number` + count in `h2`.
- **System helpers:** `stateCard`, `showNotice`, `escapeHtml`, `formatDate`.
- **Dialog/form pattern:** `.dialog-head`, `.form-grid`, `.form-error`, `.dialog-actions`, `.safety-note`.
- **Focus ring** shared `:focus-visible` outline.
- **Reduced motion** media query.
- **Skip link** / `sr-only` a11y basics.
- **Core/OSINT gateway** Python side (out of visual scope but keeps UI honest).
- **Test doubles:** `tests/support.py` `StubCore` / `StubOsint` / `WebClient` for regression after restyle.
- **Feature specs** under `docs/specs/*` describing observable states.

Нет: React/Vue components, Storybook, design-system package, icon set, router.

## 14. Control screens for before / after review

Минимальный набор (одна страница `/`, разные состояния):

| Control screen / state | Why selected | Required state |
|---|---|---|
| `/` first viewport (masthead + vacancies toolbar + 1–2 cards) | Navigation absence + hero vs board hierarchy | Populated vacancies (synthetic) |
| Vacancy card with nested OSINT research + mirrors | Density, nested surfaces, multi-button actions | Populated research + proposed confirm |
| Applications list (2+ rows) | List/table density contrast to cards | Populated journal |
| Metrics dashboard (latest + history) | Dashboard layout / nested summary cards | ≥2 metric days |
| Any create `<dialog>` open (vacancy or assessment) | Forms + primary/secondary actions | Dialog open, idle |
| Section empty `stateCard` (e.g. people) | Empty pattern | `total=0` |
| Section error `stateCard` + offline signal | Error pattern | Core unavailable / forced error |
| Optional: notice success + notice.error | Global feedback | After mutation / failed mutation |

Этого достаточно, чтобы покрыть nav gap, list vs card, detail nesting, forms, loading/empty/error без раздувания матрицы.

## 15. Recommended boundaries for R0

**Входит в R0:**

- Visual direction + project `DESIGN.md` (T-UX-00.2).
- Design tokens / page shell / global nav + active section.
- Reusable primitives: button, inputs, status/badge, surface/card, list-row, dialog chrome, loading/empty/error.
- Migration of **existing** six sections + dialogs to that foundation **без** смены бизнес-поведения.
- Control screenshots / visual review.
- Исправление typography loading и token gaps, найденных здесь.

**Не входит в R0:**

- Новые product flows (HH auth UI, Content/Telegram, Scoring provider UX redesign).
- Client-side multi-route app rewrite ради rewrite (допускается минимальная in-page nav/shell).
- Board/Kanban view (R0 готовит language «готово к List/Board», не обязан внедрять Board).
- Domain/API contract changes «под дизайн».
- Автоматический visual-regression CI (опционально позже; Gate допускает ручной review).
- DEBT-US массовое заведение; тяжёлый отдельный design-system package.

## 16. Findings summary

### Keep

- Single-origin Web facade + explicit loading/empty/error intent.
- Token-ish `:root` colors; dialog/form grid; `stateCard` / `showNotice`.
- HTTP BDD + stubs for functional regression.

### Normalize

- Buttons → one variant system.
- Section shell + spacing scale.
- Status presentation (badge/pill) with semantic colors.
- Empty vs error vs loading as distinct patterns.
- Card vs list-row density rules.

### Replace (visually, not domain)

- Marketing masthead as primary chrome → compact app header + nav.
- Hard offset neo-brutalist shadow language → спокойные surfaces per chosen DESIGN.md (decision in T-UX-00.2).
- Ad-hoc per-entity card CSS → shared surface primitives.

### Investigate in T-UX-00.2

- Сохранить ли warm paper/`--acid` accents или уйти в нейтральный productivity palette.
- List-first default для vacancies vs сохранение card grid.
- Нужны ли hash/in-page section links как interim nav до multi-page.
- Font choice with actual delivery (Inter self-host vs system vs alternative).

## 17. Next step

После согласования этого audit:

**T-UX-00.2 — сравнить реальные product references, выбрать одно visual direction и создать project-owned `DESIGN.md`.**

До отдельной команды T-UX-00.2 не начинать.

---

## Appendix A — Files inspected

**Specs / process:** `docs/R0_DESIGN.md`, `docs/R0_UI_AUDIT_TEMPLATE.md`, `README.md`, `ARCHITECTURE_PLAN.md`, `IMPLEMENTATION_PLAN.md`, `PROJECT_STATUS.md`, `AGENTS.md`, `CONTRIBUTING.md`, `DEVELOPMENT_PROCESS.md`, `services/web/README.md`, `services/web/AGENTS.md`, `services/web/docs/specs/*`.

**Web UI code:** `services/web/src/job_search_web/static/index.html`, `app.js`, `styles.css`, `app.py` (routes), `schemas.py` (touched via imports only).

**Tests:** `tests/features/vacancy_board.feature`, `tests/bdd/test_vacancy_board.py`, `tests/support.py`, `tests/integration/test_web_api.py`, `tests/contract/test_web_contract.py`, `tests/unit/test_core_client.py` (presence).
