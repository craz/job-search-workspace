# Инвентаризация модулей исходного проекта

Снимок выполнен 2026-08-15 по историческому дереву исходного монолита
(локальный архив на машине владельца). Это bootstrap-инвентаризация кода,
не runtime-источник и не шаг установки Job Search.
В снимок включены tracked, modified и untracked файлы: незакоммиченный слой OSINT
и People является частью фактической системы.

## Назначение исходных модулей

| Исходные файлы | Ответственность | Целевой репозиторий | Основные тесты |
|---|---|---|---|
| `models.py`, `statuses.py`, `domain/**`, `application/vacancies.py` | доменные сущности, статусы и правила вакансий | `job-search-core` | `test_statuses.py`, `test_vacancy_rules.py`, `test_application_vacancies.py` |
| `db.py`, `infrastructure/db/**`, `migrate_cli.py` | SQLite, миграции и repositories | `job-search-core`, с переписыванием на PostgreSQL/Alembic | `test_migrations.py`, `test_repositories.py`, `test_vacancy_repository.py` |
| `company_cli.py`, `people_cli.py`, `metrics_cli.py`, CLI vacancy/hypothesis | команды Core-сущностей | `job-search-core` | repository/server/people tests |
| `hh_*`, `application/hh_*`, CLI `hh`, HH shell scripts | HH API, browser, sync, apply, chats, applicant | `job-search-hh` | все `test_hh_*`, apply tests, fixtures HH |
| `ollama_*`, `vacancy_scoring*`, `score_*`, scoring prompts/scripts | правила и LLM-оценка | `job-search-scoring` | scoring, benchmark, compare, verdict tests |
| `osint/**`, `osint_cli.py`, `company_resolve.py` | поиск сайтов, вакансий и людей, provenance | `job-search-osint` | все `test_osint_*`, `test_people_company_resolve.py` |
| `board.py`, `board_bg.py`, `server.py`, `interfaces/views/**` | HTML-доска и текущий смешанный HTTP server | `job-search-web`; доменные API routes выделить в Core | board и server tests |
| `application/drafts.py`, `telegram_*`, `cover_letter.py`, `reports.py`, templates/prompts | drafts, отчёты и Telegram | `job-search-content` | telegram, cover letter, report tests |
| `hermes_*`, CLI `hermes`, `hermes.manifest.yaml`, install/bridge docs | адаптер локального Hermes | остаётся локально; позже `job-search-hermes` | `test_hermes_*` |
| `config.py`, `infrastructure/paths.py`, `http_client.py` | общая конфигурация и технические helpers | не копировать общей библиотекой; реализовать локально у владельца | `test_config.py` и consumer tests |

## Файлы, не переносимые в продуктовые репозитории

- `.env`, `data/**`, `drafts/*.md`, `hirer/**`, `resume/**`, `audio/**`,
  `transcripts/**`, `tmp/**` — пользовательские или runtime-данные; мигрируются
  отдельно в volumes, без публикации содержимого.
- `.venv/**`, caches, logs, PID/state-файлы и generated `board.html` — пересоздаются.
- `.cursor/**`, локальные session/context-файлы — не являются продуктовым кодом;
  новые репозитории получают только общий стандарт разработки.

## Критические границы

- Core — единственный владелец реляционной модели и PostgreSQL.
- HH, Scoring, OSINT, Content и Web не импортируют Python-модули Core и не
  подключаются к его базе.
- `server.py` нельзя переносить целиком: UI routes принадлежат Web, CRUD и
  lifecycle API — Core, Ollama/OSINT routes становятся вызовами сервисов.
- Hermes на этом этапе не меняется и использует будущий JSON CLI-контракт.
