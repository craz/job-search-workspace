# Job Search Workspace

Workspace для разделения исходного `/data/Projects/job_search` на независимые
проекты с собственными Git-репозиториями, контрактами и жизненным циклом.

Публичные сервисы проектируются как самостоятельные, воспроизводимые и
документированные проекты, понятные без доступа к приватному workspace.

> Сейчас репозиторий находится на стадии проектирования и подготовки процесса.
> Исполняемые сервисы и `compose.yaml` ещё не созданы.

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
- [Полный процесс разработки](DEVELOPMENT_PROCESS.md)
- [Правила участия](CONTRIBUTING.md)
- [Инструкции агентам](AGENTS.md)
- [Локальная история работы с AI](docs/AI_HISTORY.md)
- [Шаблон feature spec](docs/templates/FEATURE_SPEC.md)
- [Шаблон ADR](docs/templates/ADR.md)

Cursor Rules находятся в [`.cursor/rules`](.cursor/rules). Они задают безопасный
автокоммит, contract-first разработку, тестовые gates, Docker/data security,
автоматический venv, live browser/hot reload и обновление документации.

## Планируемый developer experience

После создания каркасов основной цикл будет выглядеть так:

```bash
make bootstrap  # клонировать совместимые продуктовые репозитории
make doctor     # проверить Docker, конфигурацию и host Ollama
make dev        # поднять dev stack с hot reload
make logs       # посмотреть состояние сервисов
make test       # запустить общий набор проверок
```

На этапе workspace 0A уже доступны `make bootstrap`, `make doctor`,
`make doctor-offline`, `make unit`, `make bdd` и `make test`. Команды `dev`,
`logs`, `backup` и `restore` будут добавляться в 0B вместе с реальными сервисами,
PostgreSQL и volumes.

Для host Python tooling каждый репозиторий будет содержать `.envrc`: после
однократного `direnv allow` окружение `.venv` активируется автоматически при
входе в каталог. `scripts/ensure-venv.sh` остаётся fallback для Make, CI и
агентских команд, поэтому вручную выполнять `source .venv/bin/activate` не
потребуется.

Рабочая PostgreSQL, browser profile HH, токены, кэши и drafts будут храниться в
Docker named volumes. Обычный restart или `docker compose down` их не удаляет.

## Локальная AI-история

Пользователь может создать приватное хранилище оригинальных сессий Codex, Cursor
и других AI-инструментов вместе с отдельным summary-журналом:

```bash
scripts/init-ai-history.sh
```

Новые локальные Codex-сессии подключаются и derived-представление обновляется
идемпотентной командой `make ai-history-sync`.

Правила находятся в Git. Оригинальные platform exports сохраняются в
`.local/sessions/`, производные представления — в `.local/derived/`, а всё
пользовательское содержимое остаётся вне Git.
