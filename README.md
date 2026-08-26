# Job Search Workspace

Workspace независимых Git-репозиториев Job Search с собственными контрактами и
жизненным циклом. Canonical clone самодостаточен: старый монолит не нужен для
bootstrap, Compose или чистой PostgreSQL.

Сервисы подключены как Git submodules под `services/`: workspace открывается в
IDE одним деревом, а каждый сервис сохраняет собственный remote и release cycle.

При создании долгоживущего инстанса сервиса или другой инфраструктурной сущности
используется [`NAMING_CONVENTION.md`](NAMING_CONVENTION.md): сначала выбирается
класс и свободный canonical slug, затем после назначения обновляется `USED`.
Обычные Compose services и временные контейнеры получают функциональные имена.

Публичные сервисы проектируются как самостоятельные, воспроизводимые и
документированные проекты, понятные без доступа к приватному workspace.

Первый исполняемый контур уже доступен: PostgreSQL 17, Core
Vacancy/Application/Daily Metric/Person/Hypothesis/Assessment API и Web-доска с локальным журналом
откликов, дневными показателями и подтверждёнными контактами запускаются
совместно через корневой `compose.yaml`.

## Целевая система

- `job-search-core` — домен, FastAPI и PostgreSQL;
- `job-search-hh` — HH API, Chromium, Playwright и noVNC;
- `job-search-scoring` — оценка вакансий через host Ollama;
- `job-search-osint` — исследование компаний и людей;
- `job-search-content` — черновики и Telegram;
- `job-search-web` — доска через Core API;
- `job-search-hermes` — отдельный будущий этап, текущая локальная установка не меняется.

## Документация

- [Архитектурный план](ARCHITECTURE_PLAN.md)
- [Пошаговый план реализации](IMPLEMENTATION_PLAN.md)
- [Design system (R0)](DESIGN.md)
- [Состояние проекта](PROJECT_STATUS.md)
- [Полный процесс разработки](DEVELOPMENT_PROCESS.md)
- [Правила участия](CONTRIBUTING.md)
- [Инструкции агентам](AGENTS.md)
- [Локальная история работы с AI](docs/AI_HISTORY.md)
- [Шаблон feature spec](docs/templates/FEATURE_SPEC.md)
- [Шаблон ADR](docs/templates/ADR.md)

Cursor Rules находятся в [`.cursor/rules`](.cursor/rules). Они задают безопасный
автокоммит, contract-first разработку, тестовые gates, Docker/data security,
автоматический venv, live browser/hot reload и обновление документации.

## Developer experience

Основной цикл для реализованного Core/Web-контура:

```bash
git clone --recurse-submodules <workspace-url>
make bootstrap  # инициализировать отсутствующие submodules
make doctor     # проверить Docker, конфигурацию и host Ollama
make up         # ensure HH host-proxy bridge (если нужен) + поднять stack
make dev        # то же в foreground с hot reload
make logs       # посмотреть состояние сервисов
make test       # запустить общий набор проверок
make compose-smoke  # проверить все реализованные Core/Web ресурсы
make down       # остановить контейнеры и HH host-proxy relay
```

`make up` / `make dev` перед Compose вызывают
`scripts/host_http_proxy_socket.py ensure`: если в `services/hh/.env` указан
**loopback HTTP proxy**, он пробрасывается в Docker через Unix socket + сервис
`hh-egress` (см. [`docs/runbooks/hh-docker-host-proxy.md`](docs/runbooks/hh-docker-host-proxy.md)).
Не используйте голый `docker compose up` с `HTTP_PROXY=http://127.0.0.1:…` —
контейнеры обычно не видят host loopback.

`make dev` монтирует `services/core/src` и `services/web/src` в контейнеры,
перезапускает затронутый Uvicorn-процесс после изменения Python и автоматически
обновляет уже открытую Web-страницу после изменения browser assets. Изменения
зависимостей, Dockerfile, Compose и миграций по-прежнему требуют контролируемой
пересборки через повторный `make dev`.

Доступны `make bootstrap`, `make doctor`, `make doctor-offline`, `make unit`,
`make bdd`, `make test`, `make build`, `make up`, `make dev`, `make logs`, `make down` и
`make compose-smoke`. Backup/restore будут добавлены отдельным инкрементом 0B.

Зафиксированный workspace commit содержит точные gitlink SHA сервисов. Изменение
сервиса сначала коммитится и публикуется в его собственном репозитории, затем
обновлённый gitlink отдельно фиксируется в workspace.

Для host Python tooling каждый репозиторий будет содержать `.envrc`: после
однократного `direnv allow` окружение `.venv` активируется автоматически при
входе в каталог. `scripts/ensure-venv.sh` остаётся fallback для Make, CI и
агентских команд, поэтому вручную выполнять `source .venv/bin/activate` не
потребуется.

Рабочая PostgreSQL, browser profile HH, токены, кэши и drafts будут храниться в
Docker named volumes. Обычный restart или `docker compose down` их не удаляет.

Scoring запускается без GPU и model weights в контейнере: Core доступен по HTTP,
host Ollama — через loopback в host network, raw/cache хранится в `scoring-state`.

## Локальная AI-история

Пользователь может создать приватное хранилище оригинальных сессий Codex, Cursor
и других AI-инструментов вместе с отдельным summary-журналом:

```bash
scripts/init-ai-history.sh
```

Новые локальные Codex-сессии подключаются и derived-представление обновляется
идемпотентной командой `make ai-history-sync`.

После доверия к workspace project hooks Codex и Cursor автоматически запускают
безопасную fail-open синхронизацию в конце каждого agent turn. Ручная команда
остаётся fallback; подробности и границы Cursor transcripts описаны в
[`docs/AI_HISTORY.md`](docs/AI_HISTORY.md).

Правила находятся в Git. Оригинальные platform exports сохраняются в
`.local/sessions/`, производные представления — в `.local/derived/`, а всё
пользовательское содержимое остаётся вне Git.
