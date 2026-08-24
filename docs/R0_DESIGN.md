# R0 Design — PB-UX-00

**Product:** Job Search  
**Roadmap stage:** R0 — Привести Web в рабочий визуальный вид  
**Status:** **PB-UX-00 CLOSED** — Gate R0 **ACCEPTED WITH NON-BLOCKING DEBT** (2026-08-22). R0 is no longer current implementation work.  
**Source of product truth:** UJM v1 → Product Backlog → Roadmap v1

## 1. Цель R0

Привести текущий Web в рабочий визуальный вид до добавления новых пользовательских flow.

Редизайн выполняется поверх текущей реализации и не требует ждать revision общей архитектуры.

Цель R0 — не декоративно "освежить" интерфейс, а создать устойчивую визуальную основу, на которой дальше можно строить R1-R5 без появления новых локальных стилей и конфликтующих UI-паттернов.

R0 не должен:
- перепроектировать UJM;
- менять сервисные boundaries без отдельного требования;
- менять доменные контракты только ради UI;
- превращаться в отдельный тяжёлый design-system project;
- начинать функциональность следующих Roadmap stages.

## 2. Целевое визуальное направление

Стартовая гипотеза R0:

Job Search должен двигаться в сторону спокойного, плотного рабочего B2B/productivity-интерфейса, в котором данные и состояние объектов читаются быстро, а визуальный слой не конкурирует с содержанием.

### Первый структурный референс — Asana

Asana используется как первый структурный референс, но НЕ как шаблон для копирования.

Что нас в Asana интересует:

- list-first philosophy;
- высокая информационная плотность без визуального шума;
- ясная иерархия страницы;
- стабильная глобальная навигация;
- metadata pills;
- компактные status patterns;
- спокойные surfaces;
- тонкие borders;
- минимум лишних shadows;
- semantic colors;
- несколько представлений одних объектов: List / Board и другие.

Предварительное соответствие предметной области:

| Asana | Job Search |
|---|---|
| Task | Vacancy |
| Project | Company / Search |
| Assignee | Contact |
| Task / Project status | Application stage / status |
| Custom fields | score / salary / source / work format |

Что НЕ копируем автоматически:

- branding Asana;
- coral palette;
- конкретные размеры компонентов;
- iOS/mobile-specific patterns;
- компоненты один в один;
- визуальные решения, которые не соответствуют Web и предметной области Job Search.

### Собственные элементы Job Search

Компоненты без прямого аналога в Asana проектируются самостоятельно:

- AI scoring;
- scoring explanations;
- OSINT / provenance;
- CandidateProfile / resume context;
- связь вакансии, отклика, канала и результата;
- будущие аналитические элементы поиска работы.

### К чему стремимся

- список вакансий и их состояние — основная рабочая поверхность;
- высокая density без ощущения перегруза;
- понятная page hierarchy;
- стабильная global navigation;
- metadata и статусы компактны;
- цвет используется семантически, а не декоративно;
- одинаковые сущности и действия выглядят одинаково во всём Web;
- интерфейс готов к дальнейшим List / Board представлениям без смены visual language;
- ежедневная работа в desktop Web не вызывает желания сначала переделать интерфейс.

Целевой результат R0 — не "сделать Job Search похожим на Asana", а выработать собственный visual language Job Search на основе реальных продуктовых референсов.

После UI audit и сравнения нескольких референсов направление фиксируется в project-owned `DESIGN.md`, который становится визуальной основой для R1-R5.

## 3. Исследование и референсы

Refero рассматривается как инструмент поиска референсов, flows и UX-паттернов, а не как источник готового CSS, component tree или design system.

Бесплатный рабочий маршрут исследования:

```text
SaaSUI / Nicelydone / публичные экраны реальных продуктов
    ↓
10–15 отобранных референсов
    ↓
open-source DESIGN.md / product references
    ↓
project-owned DESIGN.md Job Search
```

Проверенный reference material:
- `Meliwat/awesome-ios-design-md` содержит Asana `DESIGN.md` и platform-specific варианты;
- этот материал используется как reference, а не как нормативная Web-спецификация;
- исходные reference notes при необходимости можно хранить в `docs/design-references/`.

## 4. Правило проверки R0

Визуальные требования принимаются через:
- review текущих экранов;
- контрольные screenshots;
- сравнение ключевых состояний до / после.

BDD/Gherkin используется только для наблюдаемого поведения интерфейса.

DEBT-US не создаются заранее. Конкретный technical debt фиксируется только после UI audit и только если он реально найден в коде.

## 5. US / TECH-US

### US-UX-00.1. Единый визуальный язык текущего Web

Как пользователь, я хочу воспринимать основные экраны Job Search как части одного продукта, чтобы интерфейс не отвлекал от работы и не требовал каждый раз заново разбираться в визуальной логике.

#### Acceptance Criteria

- зафиксирована единая иерархия типографики;
- используется единая система отступов и плотности;
- основные surfaces, containers, cards и tables оформлены согласованно;
- одинаковые сущности и статусы не выглядят по-разному без смысловой причины;
- ни один основной текущий экран не остаётся в визуально несовместимом legacy-виде.

BDD: не требуется; проверяется visual review и контрольными screenshots.

---

### US-UX-00.2. Понятная навигация и иерархия страницы

Как пользователь, я хочу сразу понимать, где нахожусь и что на странице главное, чтобы быстро переходить между рабочими разделами и не искать основные действия.

#### Acceptance Criteria

- global navigation одинакова на основных экранах;
- текущий раздел визуально определим;
- у страницы есть понятный заголовок и основная рабочая область;
- primary actions отделены от secondary actions;
- одинаковые переходы не реализованы несколькими конфликтующими паттернами.

#### BDD / Gherkin

```gherkin
Scenario: Текущий раздел виден в глобальной навигации
  Given пользователь открыл основной экран Job Search
  When экран полностью загружен
  Then глобальная навигация отображается
  And текущий раздел визуально обозначен как активный
```

---

### US-UX-00.3. Единые интерактивные элементы и системные состояния

Как пользователь, я хочу, чтобы кнопки, формы, статусы и состояния загрузки / пустого результата / ошибки вели себя предсказуемо.

#### Acceptance Criteria

- button/input/select/textarea/status patterns выглядят и ведут себя одинаково;
- loading, empty, error и success/confirmation состояния имеют единый паттерн;
- destructive и primary actions визуально различимы по смыслу;
- disabled/processing состояния не выглядят как доступное действие;
- существующая бизнес-функциональность не меняется только ради редизайна.

#### BDD / Gherkin

```gherkin
Scenario: Экран показывает состояние загрузки
  Given данные экрана ещё загружаются
  When пользователь открывает экран
  Then интерфейс показывает единое loading state
  And недоступные действия не выглядят готовыми к выполнению

Scenario: Экран показывает ошибку загрузки
  Given данные экрана не удалось получить
  When загрузка завершается ошибкой
  Then интерфейс показывает единое error state
  And пользователь понимает, что данные не загружены
```

---

### TECH-US-UX-00.4. Reusable UI foundation

Как разработчик Web, я хочу иметь небольшой набор общих UI primitives и design tokens, чтобы новые экраны R1-R5 строились на той же визуальной основе.

#### Acceptance Criteria

- визуальные значения вынесены в ограниченный набор tokens/variables или эквивалент существующего стека:
  - typography;
  - spacing;
  - semantic colors;
  - borders/radius;
  - основные размеры;
- определён общий page shell/layout;
- reusable primitives покрывают минимум:
  - button;
  - form controls;
  - status/badge;
  - card/surface;
  - table/list;
  - loading/empty/error states;
- новые экраны используют foundation без копирования целого набора локальных стилей;
- решение не вводит отдельный тяжёлый design-system project.

BDD: не требуется; проверяется code review и использованием foundation.

---

### US-UX-00.5. Миграция текущих экранов без функциональной регрессии

Как пользователь, я хочу получить новый дизайн на уже работающих экранах без потери существующих возможностей.

#### Acceptance Criteria

- до изменений составлен inventory текущих экранов и ключевых состояний;
- все основные текущие экраны переведены на новую визуальную основу;
- существующие пользовательские действия остаются доступны;
- редизайн не меняет domain contracts и service boundaries без отдельного требования;
- найденные функциональные дефекты фиксируются отдельно и не маскируются под redesign work.

BDD: существующие функциональные сценарии должны продолжать проходить; новые BDD добавляются только при изменении поведения.

---

### TECH-US-UX-00.6. Контроль визуальной регрессии

Как разработчик Web, я хочу иметь воспроизводимый способ сравнить ключевые экраны до и после изменений, чтобы дальнейшие R1-R5 не разрушали визуальный фундамент незаметно.

#### Acceptance Criteria

- определён минимальный набор контрольных экранов/состояний;
- для них можно получить воспроизводимые screenshots либо эквивалентный visual-check artifact;
- проверка входит в review изменений визуального слоя;
- автоматизация visual regression допускается позже и не является обязательной для Gate R0.

## 6. Tasks R0

### T-UX-00.1. UI audit

Провести inventory:
- экранов;
- routes;
- layouts;
- компонентов;
- navigation patterns;
- typography;
- spacing;
- colors/surfaces;
- system states;
- реального technical debt;
- контрольных экранов для before/after review.

**Артефакт:** `docs/R0_UI_AUDIT.md`

На текущем шаге выполняется только этот task.

### T-UX-00.2. Visual direction + DESIGN.md

На основе UI audit и отобранных референсов:
- сравнить несколько реальных product references;
- выбрать одно целевое visual direction;
- зафиксировать контрольные примеры ключевых экранов;
- создать project-owned `DESIGN.md` Job Search;
- не строить несколько параллельных тем.

### T-UX-00.3. Design tokens + page shell

Определить минимальные design tokens/variables и общий page shell.

### T-UX-00.4. Reusable UI primitives

Реализовать reusable primitives, необходимые текущим экранам.

### T-UX-00.5. Global navigation / layout

Перевести глобальную навигацию и общий layout на новую основу.

**Принято (T-UX-00.5):**

- persistent left nav (desktop); на узком viewport — горизонтальная сетка из DESIGN tokens (без off-canvas);
- hash deep links: `#vacancies` (default), `#journal`, `#metrics`, `#people`, `#hypotheses`; legacy `#assessments` → `#vacancies`;
- unknown hash → Vacancies + `history.replaceState('#vacancies')`;
- legacy `#applications` → `#journal` (DOM id `#applications` для списка откликов сохранён);
- одна `.section-view` visible; inactive через HTML `hidden` + `.section-view[hidden]`;
- active nav: `aria-current="page"` + accent inset (не только цвет);
- browser back/forward через native `hashchange`;
- notice глобально в начале `main`; dialogs вне section views.

### T-UX-00.6. Migration existing screens

Последовательно мигрировать текущие основные экраны без изменения их продуктовой функции.

**Принято (T-UX-00.6):**

- все **пять** top-level sections — **list-first** collections (`.list-rows`, `.list-row`, `.list-row-group`);
- Vacancies: compact row + `<details class="row-detail">` для OSINT/mirrors/evidence + **Assessment summary in row** (IA correction T-UX-00.8);
- Metrics: `surface--panel` + `.metric-cell` grid + compact history bars;
- Assessments: **no standalone section**; reason/risk/action in vacancy expand; full flow → R2/PB-03;
- все dialogs/forms — `.dialog__*`, `.field`, `.control`;
- domain statuses через `.badge` (vacancy, person, hypothesis, assessment verdict);
- row actions — `.btn--secondary` / `.btn--ghost`; section CTA — `.btn--primary`;
- удалены legacy card/grid CSS и unused button aliases;
- **visual review (post-migration):** исправлены proportions `.list-row` (primary flexible + trailing auto); section counts отделены от заголовков; убрана prototype numbering в toolbars; Journal date compact; Assessments disclosure inline в trailing row;
- **visual review (review3):** compact nav width (`--nav-width: 10.5rem`); collection screens на full-width main; Metrics dashboard с локальным `max-width`;
- **dark scheme (T-UX-00.6):** R0 primary UI = dark productivity; semantic tokens, no theme switch;

### T-UX-00.7. System states

**Принято (T-UX-00.7):**

- unified `.state--loading|empty|error` для section states; `.notice--success|error|info|warning` для shell feedback;
- `.inline-state--empty|error|loading` для nested OSINT/detail regions;
- Retry на section errors; optional empty CTA там, где есть section create action;
- `.is-processing` на async submit/OSINT controls; legacy `.state-card` удалён;

### T-UX-00.8. Regression + visual review (+ IA correction)

**Принято (T-UX-00.8):**

- Web `make test` — green after review2 + IA5;
- top-level **«Оценки» removed**; five-section nav; Assessment contextual in Vacancy row (existing `/api/v1/assessments` client join);
- Assessment API/domain unchanged; manual record dialog removed from UI (deferred R2/PB-03);
- system states verified (live + stub): loading/empty/error/offline/notice/inline OSINT;
- acceptance: [`docs/R0_ACCEPTANCE.md`](R0_ACCEPTANCE.md) — **READY FOR GATE R0**;
- screenshots: `docs/r0/screenshots/t-ux-00.8-ia5/`

### T-UX-00.9. Gate R0 — COMPLETE

**2026-08-22:** Gate R0 **ACCEPTED WITH NON-BLOCKING DEBT** with product owner.

Accepted: Calm Dense Productivity, dark primary scheme, five-section IA, Assessment contextual to Vacancy, Web tests 37 passed @ `86f37cb`.

Non-blocking debt (cursor-rule test, legacy naming, demo duplicates, housekeeping) — не reopen R0 без architecture blocker.

Record: [`docs/R0_ACCEPTANCE.md`](R0_ACCEPTANCE.md).

## 7. Definition of Done / Gate R0

PB-UX-00 считается завершённым, когда:

- основные текущие экраны приведены к одной визуальной системе;
- существующие пользовательские действия работают;
- глобальная навигация и page hierarchy согласованы;
- reusable foundation используется в Web;
- loading / empty / error / status states согласованы;
- ключевые control screens прошли visual review;
- визуальный результат принят как достаточный для ежедневной работы;
- R1 можно реализовывать уже на новой визуальной основе.

## 8. Текущий next step

```text
R0 / PB-UX-00
    ↓
T-UX-00.1 UI audit                 ✓
    ↓
T-UX-00.2 visual direction + DESIGN.md  ✓
    ↓
T-UX-00.3 tokens + page shell           ✓
    ↓
T-UX-00.4 reusable primitives              ✓
    ↓
T-UX-00.5 global navigation / layout        ✓
    ↓
T-UX-00.6 migration + dark scheme         ✓
    ↓
T-UX-00.7 system states                  ✓
    ↓
T-UX-00.8 regression + visual review      ✓
    ↓
T-UX-00.9 Gate R0 with product owner      ✓
    ↓
revision ARCHITECTURE_PLAN.md + IMPLEMENTATION_PLAN.md
    ↓
PB-DATA-00 (one-time owner bootstrap; completed and isolated)
```

Норматив: [`DESIGN.md`](../DESIGN.md). Acceptance: [`R0_ACCEPTANCE.md`](R0_ACCEPTANCE.md). Research: [`R0_DESIGN_REFERENCES.md`](R0_DESIGN_REFERENCES.md).

R0 closed. Следующая реализационная работа — не R0; см. Roadmap и revision планов.
