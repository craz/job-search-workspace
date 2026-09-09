# Job Search

**Local-first AI-система для управления поиском работы: резюме → подходящие вакансии → AI-оценка → решение → отклик → найм → оффер → завершение поиска.**

Проект родился из собственного поиска работы. Его цель — собрать разрозненный процесс в один управляемый pipeline: подключить HeadHunter, сохранить контекст и версии резюме, собирать и дедуплицировать вакансии, оценивать их локальной LLM и вести историю решений, откликов и результатов.

`Local-first` · `HeadHunter integration` · `Resume-aware scoring` · `Active development`

![Job Search — экран вакансий](docs/assets/readme/job-search-hero-wide.png)

## Зачем появился Job Search

Когда вакансий становится сотни, поиск работы перестаёт быть задачей «найти и откликнуться». Нужно помнить, каким резюме ты вышел на компанию, какие вакансии уже видел, где откликнулся, что ответили, какие гипотезы сработали и когда пора менять стратегию. В браузерных вкладках, заметках и истории HeadHunter этот контекст быстро распадается.

Job Search я сделал для себя как единый рабочий контур: вакансии, решения, отклики и результаты остаются связаны с конкретной версией резюме и периодом поиска. AI здесь не заменяет решение пользователя — он помогает быстрее разобрать большой поток и выделить то, что стоит внимания.

## Как работает Job Search

Job Search ведёт вакансию через весь путь — от появления в списке до решения, контакта с работодателем, процесса найма и итогового результата.

![Как работает Job Search](docs/assets/readme/job-search-flow.png)

Функциональный user journey (find → score → decide → act → response → hiring → offer → close search) реализован в продукте. Периодная аналитика (PB-11) и clean-install на чужой машине (Final Gate) — отдельные release-пункты.

## Что умеет Job Search

### ✅ Уже работает

**HeadHunter integration** — рабочее резюме, PDF-артефакт, список подходящих вакансий.  
**Vacancy pipeline** — импорт, дедуп, рабочая очередь.  
**Resume-aware AI scoring** — локальная оценка через Ollama (без Ollama доска всё равно работает).  
**Owner decisions / action channel** — interested / deferred / skipped / applied + HH / DIRECT / BOTH.  
**Applications, DirectOutreach, EmployerResponse** — локальные факты без автоотправки.  
**Hiring process** — этапы, активности, deadlines, next_action.  
**Offers** — условия, сравнение, accept/decline.  
**Search cycle close** — явное завершение поиска после accepted Offer; automation останавливается.

### 🗺️ Дальше по roadmap

**Периодные метрики и корректировка стратегии (PB-11)** — аналитический контур поверх уже накопленной истории.  
**Release readiness / Final Gate** — воспроизводимый clean install (этот документ + `docs/runbooks/local-stack.md`).

## Архитектура

![Архитектура Job Search](docs/assets/readme/job-search-service-map.png)

Job Search разбит на независимые сервисы с собственными границами ответственности. Core владеет доменными данными и публичными API-контрактами; интеграции с HeadHunter, AI-scoring и OSINT вынесены в отдельные сервисы.

## Tech stack

`Python` · `FastAPI` · `PostgreSQL 17` · `Docker Compose` · `Playwright / Chromium` · `Ollama` · `Vanilla Web`

## Запуск локально (clean install)

**Prerequisites:** Linux, Git, Docker + Compose plugin, Python 3.12+, Make.  
Optional: `direnv`, host Ollama + scoring model, HH OAuth credentials.

```bash
git clone --recurse-submodules https://github.com/craz/job-search-workspace.git
cd job-search-workspace
make bootstrap          # submodules at locked gitlinks + create .env / services/hh/.env from examples
make doctor             # tools, revisions, env presence (use --offline without network)
make up                 # canonical start: host bridges + Compose build/up
make status             # compose ps + HTTP probes
```

| Surface | Default URL |
|--|--|
| Web | http://127.0.0.1:8080/ |
| Core | http://127.0.0.1:8000/docs |

Ports override via `.env` (from [`.env.example`](.env.example)). HH credentials stay in `services/hh/.env` (from `services/hh/.env.example`) — never commit real tokens.

```bash
make down               # stop stack + host bridges
make up                 # restart
make install-autostart  # optional machine boot → make boot
```

Working-DB fixture cleanup (PB-DATA-01): [`docs/PB_DATA_01_WORKING_DB_CLEANUP.md`](docs/PB_DATA_01_WORKING_DB_CLEANUP.md).  
Daily ops detail: [`docs/runbooks/local-stack.md`](docs/runbooks/local-stack.md).

HeadHunter after first start usually needs interactive login/session. Without HH/Ollama the Web still opens; acquisition/scoring degrade with clear UI/API errors. Automation defaults to **disabled**.

## Документация

- [Local stack runbook](docs/runbooks/local-stack.md) — start/stop, URLs, automation, degraded mode
- [Architecture](ARCHITECTURE_PLAN.md) — границы сервисов
- [Project goal](docs/PROJECT_GOAL.md) — long-term direction
- [Scoring](services/scoring/README.md) — Ollama scoring
- [Design](DESIGN.md) — UI rules
- [Contributing](CONTRIBUTING.md) — change flow
