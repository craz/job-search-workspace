# Карта миграции

## Правило назначения

Каждый исполняемый модуль получает одного владельца. Если исходный файл смешивает
ответственности, он декомпозируется; целевые репозитории не получают две копии
одной бизнес-логики.

| Исходная область | Цель | Действие |
|---|---|---|
| domain/models/statuses/application vacancies | Core | перенести правила, заменить persistence ports |
| SQLite repositories/migrations | Core | переписать на SQLAlchemy 2/Alembic/PostgreSQL; затем одноразовый importer |
| company/people/hypothesis/metrics/vacancy CLI | Core | заменить на versioned JSON CLI/API |
| `hh_*`, HH application services и scripts | HH | перенести по вертикальным срезам; DB calls заменить Core client |
| Ollama/scoring/benchmark/compare | Scoring | выделить очередь, cache volume и Assessment contract |
| `osint/**`, resolver и OSINT CLI | OSINT | сохранить provenance локально, confirmed result отправлять в Core |
| board/views и UI часть server | Web | заменить SQLite/repository access на Core API client |
| drafts/reports/cover/Telegram | Content | локальные drafts/journal volume, Core summary client |
| Hermes modules | отложено | не трогать текущую host-установку |

## Порядок переноса и зависимости

1. Core contract и PostgreSQL становятся provider foundation.
2. Web первым доказывает чтение/изменение вакансии только через API.
3. HH переносит read/sync до любых реальных apply operations.
4. Scoring создаёт Assessment через Core.
5. OSINT передаёт подтверждённые Company/Person.
6. Content потребляет безопасную сводку и ведёт свой журнал.
7. Workspace фиксирует совместимые SHA и добавляет cross-service smoke.

## Тесты при переносе

- Core: migrations, repositories, vacancy/application/status/company/people.
- HH: parser/API/browser/login/sync/apply/chat/applicant; реальные отправки всегда
  заменены fake transport или dry-run.
- Scoring: rules, Ollama timeout/degradation, cache, benchmark и verdict override.
- OSINT: domain/site/vendor/people/pipeline с синтетическими fixtures.
- Web: board data/render/charts/API states и browser smoke.
- Content: drafts, cover letter, Telegram HTML/fetch/preview/publish fake.

## Нерешённые решения перед копированием кода

- Зафиксировать точный исходный commit плюс hash незакоммиченного snapshot либо
  сначала архивировать patch: текущий источник dirty.
- Утвердить PostgreSQL типы/UUID и правила импорта legacy integer IDs.
- Разделить `server.py` route-by-route и определить sync/async job contracts.
- Решить судьбу legacy `recommend`, `hirer` и `parse` команд без автоматического
  включения их в новый публичный API.
