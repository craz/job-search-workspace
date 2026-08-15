# Contributing

Полный процесс разработки описан в
[`DEVELOPMENT_PROCESS.md`](DEVELOPMENT_PROCESS.md), архитектура — в
[`ARCHITECTURE_PLAN.md`](ARCHITECTURE_PLAN.md).

Короткий путь изменения:

1. Создать ветку `type/short-kebab-scope` от актуальной `main`.
2. Зафиксировать scope, non-scope и acceptance criteria.
3. Для новой возможности создать feature spec; для архитектурного решения — ADR.
4. Реализовать минимальный вертикальный срез.
5. Запустить применимые `make` quality gates и просмотреть diff.
6. Обновить документацию и `CHANGELOG.md` продуктового репозитория.
7. Создать PR, заполнить чеклист и дождаться зелёного CI/review.

Коммиты используют Conventional Commits:

```text
feat(core): add idempotent vacancy import
fix(hh): retain browser session after restart
docs(workspace): document volume restore
```

Не коммитьте `.env`, токены, cookies, browser profiles, дампы БД, volumes,
черновики с персональными данными и реальные ответы внешних сервисов.

