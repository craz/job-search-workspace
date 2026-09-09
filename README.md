# Job Search

**Local-first AI-система для ежедневного поиска работы.**

**v1 · PROJECT_GOAL → COMPLETE**

`Local-first` · `HeadHunter` · `Resume-aware scoring` · `Hiring & offers`

![Job Search — экран вакансий](docs/assets/readme/job-search-hero-wide.png)

## Зачем

Когда вакансий становится сотни, поиск работы перестаёт быть задачей «найти и откликнуться». Нужно помнить резюме, решения, отклики, ответы, этапы найма и офферы в одном контуре. Job Search — персональный local-first инструмент для этого процесса.

## Journey (v1)

find → score → decide → act → response → hiring → offer → compare → accept → close search cycle

Продукт пригоден для ежедневного использования через Web без ручного ремонта через Cursor/SQL.

## Что умеет

- **HH** — резюме, PDF-артефакт, подходящие вакансии  
- **Pipeline** — импорт, дедуп, очередь разбора  
- **Scoring** — локальная оценка через Ollama (без Ollama доска всё равно работает)  
- **Решения и канал** — interested / deferred / skipped / applied · HH / DIRECT / BOTH  
- **R3 факты** — Application, DirectOutreach, EmployerResponse (без автоотправки)  
- **Найм** — этапы, активности, deadlines, next_action  
- **Офферы** — условия, сравнение, accept/decline  
- **Search cycle** — явное завершение поиска после accepted Offer  
- **Automation** — owner-controlled fetch→ingest→score; по умолчанию выключена  

## Запуск

Canonical start:

```bash
git clone --recurse-submodules https://github.com/craz/job-search-workspace.git
cd job-search-workspace
make bootstrap
make up
make status
```

| Surface | Default URL |
|--|--|
| Web | http://127.0.0.1:8080/ |
| Core | http://127.0.0.1:8000/docs |

Основные сервисы: Core, Web, HH, Scoring, Automation (+ Postgres, RabbitMQ, OSINT/SearXNG).  
Порты — `.env` из [`.env.example`](.env.example). Секреты HH — только в `services/hh/.env` (из example).

```bash
make down
make up
make doctor
make install-autostart   # optional
```

Подробности: [`docs/runbooks/local-stack.md`](docs/runbooks/local-stack.md).  
Clean-install / release readiness (PB-REL-00) и очистка fixture-данных (PB-DATA-01) пройдены.

## Архитектура

![Архитектура Job Search](docs/assets/readme/job-search-service-map.png)

Независимые сервисы с HTTP-контрактами. Core — каноническое доменное состояние.

## Tech stack

`Python` · `FastAPI` · `PostgreSQL 17` · `Docker Compose` · `Playwright` · `Ollama` · `Vanilla Web`

## Статус v1

**PROJECT_GOAL → COMPLETE** (Final Project Gate accepted).

POST-v1 / backlog (например PB-11 — периодные метрики) — **не** незавершённость v1; только явный следующий slice.

## Документация

- [Project goal](docs/PROJECT_GOAL.md) · [Project status](PROJECT_STATUS.md)  
- [Local stack](docs/runbooks/local-stack.md) · [Architecture](ARCHITECTURE_PLAN.md)  
- [Scoring](services/scoring/README.md) · [Design](DESIGN.md) · [Contributing](CONTRIBUTING.md)
