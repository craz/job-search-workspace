# План реализации Job Search Multirepo

## Текущее состояние

- Исходный `/data/Projects/job_search` остаётся неизменяемым архивом.
- Workspace и шесть продуктовых Git-репозиториев созданы.
- Remote `origin` и ветки `main` настроены.
- Архитектура и процесс разработки зафиксированы.
- Core/Vacancy MVP реализован и опубликован; HH, Scoring и OSINT имеют безопасные
  capability scaffolds, а Web развивается как первый Core consumer.
- Системная инвентаризация исходного проекта завершена и проверяется автоматически.

## 0. Управляющий workspace

Этот этап разделён на базовую часть, которая выполняется до инвентаризации, и
интеграционную часть, которая развивается вместе с сервисами. Нельзя объявлять
готовыми команды, для которых ещё не существует исполняемой системы.

### 0A. Базовый workspace — выполнить первым

**Статус:** реализован и переведён на Git submodules; `.gitmodules`, gitlinks,
безопасный bootstrap, doctor, ADR и локальные исполняемые проверки добавлены.
Gate подтверждается командами `make test`, `make bootstrap` и `make doctor`.

Добавить сейчас:

- `.gitmodules` со списком remote URL и веток сервисов;
- gitlinks с проверенными commit SHA;
- `bootstrap`, который клонирует или проверяет все репозитории;
- базовый `doctor`, который проверяет Git, Docker, direnv, доступность remote и
  соответствие локальных HEAD gitlinks;
- ADR по multirepo, PostgreSQL и межсервисной интеграции.

**Gate 0A:** workspace можно клонировать отдельно, получить все продуктовые
репозитории одной командой и проверить их версии. Архитектурные решения объяснены
без зависимости от ещё не реализованных сервисов.

### 0B. Интеграционный workspace — развивать по мере появления сервисов

- `test` появляется после стандартных Make-интерфейсов продуктовых репозиториев;
- `dev` и `logs` появляются после первого исполняемого Compose-стека;
- `backup` и `restore` появляются вместе с PostgreSQL и persistent volumes;
- `compose-smoke` появляется после Core и первого consumer;
- `doctor` расширяется проверками PostgreSQL, Core, HH/noVNC и host Ollama тогда,
  когда соответствующие компоненты реально существуют.

**Gate 0B:** каждая команда выполняет реальную проверку или операцию. Запрещены
декоративные заглушки, которые завершаются успешно без проверки системы.

## 1. Инвентаризация исходного проекта

**Статус:** завершён. Фактическое рабочее дерево описано в `docs/inventory/`;
`make inventory-check` подтверждает единственного владельца каждого code-файла,
а `source-code.lock.json` фиксирует проверенный dirty snapshot.

Для каждого исходного файла определить:

```text
исходный файл → целевой репозиторий → ответственность → зависимости → тесты
```

Зафиксировать:

- CLI-команды и HTTP endpoints;
- таблицы SQLite и миграции;
- доменные сущности и правила;
- внешние интеграции;
- файловые хранилища и фоновые процессы;
- переменные окружения и секреты;
- существующие тесты;
- межмодульные зависимости.

Артефакты:

- `docs/inventory/modules.md`;
- `docs/inventory/commands.md`;
- `docs/inventory/data.md`;
- `docs/inventory/dependencies.md`;
- `docs/inventory/migration-map.md`.

**Gate:** каждый значимый файл и сценарий назначен ровно одному репозиторию; нет
ничейной или продублированной логики.

## 2. Стандартный каркас продуктовых репозиториев

**Статус:** выполняется. `job-search-core` подготовлен как проверенный эталон:
uv lock, автоматическая `.venv` через direnv/Make, FastAPI health contracts,
versioned JSON CLI, Ruff, strict mypy, unit/integration/contract/pytest-bdd,
GitHub Actions и Docker smoke. Остальные продуктовые репозитории ещё не
адаптированы; `job-search-content` по текущему решению не изменяется.

`job-search-hh` получил безопасный scaffold без внешних интеграций: versioned
capabilities CLI явно фиксирует `external_writes_enabled=false`, HH API и browser
automation остаются `not-configured`; unit/contract/pytest-bdd и локальные quality
gates проверены. Dockerfile подготовлен, но image build сознательно не запускался
без отдельного согласования загрузки base image.

`job-search-scoring` получил безопасный host-Ollama scaffold: capability contract
фиксирует Ollama, model и Core Assessment write как `not-configured`, а прямой GPU
в container — как ненужный. Unit/contract/pytest-bdd и локальные quality gates
проверены полностью offline; Docker build и model download не выполнялись.

В Core, HH, Scoring, OSINT, Content и Web добавить:

- README и CHANGELOG;
- `pyproject.toml` и lock-файл;
- `.env.example`, `.envrc` и `.gitignore`;
- `scripts/ensure-venv.sh`;
- Makefile и Dockerfile;
- AGENTS/Cursor Rules;
- структуру `src/`, `tests/`, `tests/features/`, `tests/bdd/`;
- Ruff, typecheck, pytest и pytest-bdd;
- GitHub Actions и PR template;
- лицензию.

Стандартные команды:

```bash
make dev
make format-check
make lint
make typecheck
make unit
make integration
make contract
make bdd
make build
make smoke
```

**Gate:** каждый репозиторий независимо клонируется, автоматически активирует
`.venv` через direnv, собирает контейнер и проходит CI.

## 3. Core: первый вертикальный срез

**Статус:** завершён. PostgreSQL/Alembic, Company/Vacancy, идемпотентное
создание, чтение и смена статуса доступны через `/api/v1` и покрыты unit,
integration, contract и BDD-проверками.

Первая User Story:

```text
Как пользователь системы поиска работы,
Я хочу добавлять и просматривать вакансии,
Чтобы управлять своей воронкой поиска.
```

Реализовать:

- PostgreSQL 17;
- SQLAlchemy 2.x;
- Alembic;
- Company и Vacancy;
- статусы воронки;
- FastAPI `/api/v1`;
- версионированный JSON CLI;
- health/readiness;
- идемпотентное создание вакансий;
- OpenAPI и Gherkin-сценарии.

Затем отдельными инкрементами добавить:

1. Applications — **завершено**: миграция, идемпотентные HTTP/JSON CLI
   create/list и связь с Vacancy.
2. Daily Metrics — **завершено**: датированные replay-safe HTTP/JSON CLI
   set/show/list, отдельная миграция и bounded history.
3. People — **завершено**: подтверждённые контакты Company/Vacancy,
   идемпотентное создание, локальные статусы и Web dashboard без OSINT/messages.
4. Hypotheses — **завершено**: измеримые replay-safe эксперименты, фильтрация,
   неизменяемый результат закрытия и полный Web dashboard.
5. Assessments — **завершено в Core/Web**: нормализованные replay-safe оценки
   вакансий с объяснением, риском, действием и model/prompt metadata. Реальный
   расчёт очередью Scoring остаётся отдельным этапом 6.

**Gate:** чистая система поднимается в Docker, применяет миграции и проводит
вакансию через API/CLI без SQLite.

## 4. Web: работа через Core API

**Статус:** завершён. Независимый Web scaffold и HTTP-only Core gateway
реализуют browser flow для вакансий, локального журнала откликов, Daily Metrics
и People
dashboard; совместный Compose подтверждает PostgreSQL → Core → Web, а headless
Chrome и повторный запуск контейнеров проверяют UI и persistence. Web не
отправляет реальные отклики во внешние системы и не вычисляет метрики в обход
Core.

User Story:

```text
Как пользователь системы,
Я хочу видеть вакансии, менять их статус и фиксировать отклики в браузере,
Чтобы управлять поиском без ручных CLI-команд.
```

Реализовать:

- список и создание вакансий;
- смену статуса;
- создание и список Applications, связанных с существующей вакансией;
- явную границу между локальной записью факта и внешней отправкой отклика;
- сводку, историю и форму частичного обновления Daily Metrics;
- карточки подтверждённых людей, форму создания и локальную смену статуса;
- создание, просмотр и закрытие измеримых Hypotheses с наблюдаемым результатом;
- отображение и ручную contract-проверку нормализованных Assessments;
- loading, empty, success и error states;
- live browser и hot reload;
- BDD и browser smoke;
- доступ к данным исключительно через Core API.

**Gate:** Web не импортирует Core, не знает PostgreSQL и сохраняет данные после
перезапуска контейнеров.

## 5. HH: чтение перед отправкой

Переносить отдельными безопасными релизами:

1. Chromium, Playwright и noVNC.
2. Постоянный browser profile в Docker volume.
3. Авторизация и проверка сессии.
4. Получение вакансий.
5. Синхронизация откликов, переговоров и метрик.
6. Dry-run отклика.
7. Limited apply с лимитами, CAPTCHA-stop и аудитом.

**Gate:** сессия переживает перезапуск, синхронизация идемпотентна, BDD не
отправляет реальные отклики, а CAPTCHA/auth error безопасно останавливают процесс.

## 6. Scoring

**Статус:** реализован базовый исполняемый pipeline: persistent queue,
cancel/work-once, bounded Core/Ollama clients, private raw store и нормализованная
Assessment write. Автоматический scheduler и production retry policy остаются
следующими инкрементами.

User Story:

```text
Как пользователь системы,
Я хочу получать объяснимую оценку вакансии,
Чтобы быстрее выбирать вакансии для отклика.
```

Реализовать:

- получение вакансии через Core API;
- очередь заданий;
- обращение к host Ollama;
- сырые ответы и кэш в volume Scoring;
- нормализованный Assessment в Core;
- версию модели и prompt;
- timeout, retry, cancel и контролируемую деградацию.

**Gate:** Scoring не читает PostgreSQL напрямую и корректно работает при
недоступной Ollama.

## 7. OSINT

`job-search-osint` получил provenance-safe scaffold: capability contract явно
фиксирует providers и Core write как `not-configured`, хранение raw evidence —
как локальную ответственность OSINT, а provenance и подтверждение — как
обязательные условия. Unit/contract/pytest-bdd и quality gates пройдены offline;
внешние провайдеры, Docker build и сетевые загрузки не запускались.

Реализовать:

1. Определение сайта компании.
2. Поиск зеркала вакансии.
3. Поиск публичных профессиональных профилей.
4. Provenance и confidence.
5. Подтверждение результата.
6. Передачу подтверждённых Company/Person в Core.

**Gate:** сырые данные остаются в OSINT volume, в Core передаются только
нормализованные подтверждённые сведения, а публичные fixtures синтетические.

## 8. Content и Telegram

Реализовать отдельными инкрементами:

1. Получение публичной сводки из Core.
2. Генерация draft.
3. Preview.
4. Локальный журнал публикаций.
5. Fake Telegram transport.
6. Реальный publish/delete с явным разрешением.

**Gate:** приватные поля не попадают в preview/Telegram, BDD не использует
реальный бот, drafts сохраняются после перезапуска.

## 9. Сквозная сборка workspace

Целевой поток:

```text
HH получает вакансию
→ Core сохраняет её
→ Scoring оценивает
→ OSINT дополняет компанию
→ Web показывает результат
→ Content создаёт preview
```

Проверить:

- `make bootstrap`, `doctor`, `dev`, `test`, `compose-smoke`;
- совместимость зафиксированных версий;
- миграции PostgreSQL;
- backup/restore;
- сохранение named volumes;
- восстановление после перезапуска;
- health/readiness всех сервисов.

**Gate:** один workspace lock фиксирует полностью проверенный совместимый набор
версий всех сервисов.

## 10. Совместимость с локальным Hermes

Hermes не переносить и не контейнеризировать на этом этапе.

Выполнить только:

- подключение к публичным JSON CLI;
- проверку версий контрактов;
- сохранение существующего audit;
- проверку dry-run и лимитов;
- документирование adapter boundary.

**Gate:** Hermes работает без импорта Python-модулей новой системы и без доступа
к PostgreSQL или чужим volumes.

## 11. Отложенный `job-search-hermes`

После стабилизации остальных сервисов отдельным проектом выполнить:

- инвентаризацию существующего Hermes;
- перенос orchestration;
- собственные тесты и release cycle;
- отдельный ADR о целесообразности контейнеризации.

## Практическая последовательность

```text
Workspace foundation 0A
→ Inventory
→ Repository skeletons
→ Core/Vacancy MVP
→ Web MVP
→ Core remaining entities
→ HH read-only
→ HH dry-run/limited apply
→ Scoring
→ OSINT
→ Content
→ Workspace integration 0B / Compose E2E
→ Hermes compatibility
```

До стабильного Core API этапы выполняются последовательно. После него Scoring,
OSINT и Content технически независимы, но базовый порядок реализации остаётся
указанным выше, чтобы уменьшить число одновременно меняющихся контрактов.

## Следующий шаг

Следующая выполняемая задача — **People**: подтверждённые профессиональные
контакты как Core-owned сущность с отдельной миграцией и версионированными
HTTP/JSON CLI контрактами; сырые OSINT-ответы остаются за пределами Core.
