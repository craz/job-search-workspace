# Команды и HTTP interfaces

## CLI по целевым владельцам

| Владелец | Исходные группы команд |
|---|---|
| Core | `init`, `bootstrap`, `vacancy add/list/set-status`, `company show/list/set/resume-view/sync/upsert-from-fetch`, `people add/list/set`, `hypothesis add/list/close`, `metrics set/show/list`, `migrate status/import` |
| HH | `hh auth/status/resumes/resume/sync`, browser/login/check-login, negotiations/resume-views, capture/fetch, apply-one/apply-many/apply-plan/apply-tick/autopilot, chats/applicant |
| Scoring | `score-vacancy`, `score-first`, `score-next`, benchmark/capture/batch-summary/compare, Ollama resume sync; после переноса убрать их из namespace HH |
| OSINT | `osint site/vacancy/queries/domain/people-lookup/vendor-it/people-web/people/run` |
| Content | `draft day/week/period/vacancy`, `content list/mark-published`, `telegram fetch/check/dm-check/preview/publish/edit/delete`, `report today/week`, `export-cover` |
| Web | `serve`, `board bg-fetch`; в целевом Web это developer commands, не доменный CLI |
| Отложено | все `hermes *`, `hermes bridge *`, `hirer fetch`, `parse hirer*`, legacy `recommend *` до отдельного решения |

Все machine-facing команды при переносе получают versioned JSON envelope и
стабильные exit codes. Человеческий Rich-вывод не считается контрактом.

## Текущие HTTP routes и назначение

| Исходный route | Цель |
|---|---|
| `GET /`, `GET /assets/{filename}` | Web |
| `GET /api/dev/revision` | Web development endpoint |
| `POST /api/applications`, `GET /api/applications/{id}/cover` | Core `/api/v1` |
| `POST /api/resume-views` | Core `/api/v1` |
| `GET /api/statuses` | Core `/api/v1` |
| `GET/PATCH /api/vacancies[/ {id}]` | Core `/api/v1` |
| `PATCH /api/scores/{vacancy_id}` | заменить созданием Assessment через Core API |
| `GET /api/ollama/status` | Scoring health; Web вызывает Scoring либо агрегированный Core contract |
| `POST/GET /api/osint/{vacancy_id}` | OSINT job/status contract, не Web-owned route |
| `GET /callback` | HH OAuth callback |

Текущие routes не версионированы и смешаны в `server.py`; они являются
инвентаризацией поведения, а не контрактом для сохранения один-к-одному.

## Фоновые процессы

- `fetch-all-bg.sh` / `vacancy_fetch_pool.py` → HH worker.
- `score-ollama-bg.sh` → Scoring worker.
- `rescore-rules-bg.sh` → Scoring maintenance job.
- `hh_apply_daemon.py`, apply tick/cron/autopilot → HH, только после dry-run gates.
- `fetch_board_bg.py` → Web asset tooling.
- Hermes bridge cron → остаётся в текущей локальной установке.
