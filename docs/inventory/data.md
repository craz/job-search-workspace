# Данные и хранилища

## Реляционная схема

Текущий источник — SQLite migrations `001`–`004` и runtime
`data/job_search.db`. Целевой владелец всей нормализованной схемы — Core на
PostgreSQL 17.

| Таблица | Назначение | Решение при миграции |
|---|---|---|
| `settings` | key/value настройки | не переносить секреты; продуктовые настройки типизировать |
| `companies` | компании и HH employer metadata | Core Company; отделить HH/OSINT provenance от подтверждённых полей |
| `vacancies` | вакансия, статус, приоритет и встроенная оценка | Core Vacancy; `reason/risk/action` вынести в Assessment |
| `applications` | отклики и follow-up | Core Application |
| `hypotheses` | гипотезы поиска | Core Hypothesis |
| `daily_metrics` | дневные показатели | Core DailyMetric |
| `content_logs` | drafts/Telegram publication | перенести владение журналом в Content; Core хранит только публичную сводку при необходимости |
| `people` | профессиональные контакты | Core Person после подтверждения OSINT результата |

SQLite integer IDs нельзя обещать как публичный контракт. Импорт в PostgreSQL
должен сохранить связи через migration mapping и пройти сверку количества,
обязательных полей и внешних ключей.

## Runtime-файлы и целевые volumes

| Исходные данные | Владелец / место |
|---|---|
| `job_search.db`, schema/migration state | Core PostgreSQL named volume |
| `hh_token.json`, `hh_app_token.json`, browser profile, chat/apply state | HH named volumes |
| scoring queues, raw model responses, benchmark/cache | Scoring named volume |
| OSINT raw pages, search results и provenance | OSINT named volume |
| drafts, Telegram message journal | Content named volume |
| generated board/assets | Web image или disposable cache, не persistent domain storage |
| `hermes_audit.jsonl` и Hermes logs | остаются на хосте у локального Hermes |

## Секреты и приватные данные

Обнаружены категории переменных: HH OAuth (`HH_CLIENT_ID`, secret, redirect,
proxy, user-agent), Telegram tokens/channel/chat IDs и search date. Значения из
`.env` не читаются и не переносятся. В Git допускаются только пустые примеры и
описания. Резюме, переписки, аудио, transcripts, cover letters и реальные
вакансии не используются как публичные fixtures; тесты получают синтетические
данные.
