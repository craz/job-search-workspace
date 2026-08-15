# Зависимости и интеграции

## Текущий runtime

- Python `>=3.11`; Typer/Rich CLI.
- FastAPI/Uvicorn/Pydantic HTTP server.
- Jinja2 HTML rendering.
- BeautifulSoup и DDGS для HTML/search parsing.
- Playwright как optional browser dependency.
- SQLite из stdlib; subprocess/browser/OS background jobs.

Lock-файл зависимостей отсутствует. Версии заданы нижними границами, поэтому
исходная установка не является полностью воспроизводимой.

## Внешние системы

| Система | Текущий способ | Целевая граница |
|---|---|---|
| HH API | OAuth/HTTP | только HH |
| hh.ru Chromium | host CDP + Playwright | Chromium/Playwright/noVNC внутри HH container, profile в HH volume |
| Ollama/GPU | host HTTP/process checks | Scoring container обращается к host endpoint |
| Telegram | Bot API/widget HTML | только Content; fake transport в BDD |
| Search/websites | DDGS и прямой HTTP | только OSINT, обязательны provenance/confidence |
| Hermes | host CLI/bridge/audit | не контейнеризировать; позже только JSON CLI |

## Обнаруженные нежелательные связи

- `server.py` одновременно знает Web rendering, Core repositories, Scoring и
  OSINT jobs.
- HH CLI содержит scoring-команды и пишет прямо в SQLite.
- Content/report/draft код читает общую SQLite напрямую.
- Board data/view код читает repositories и runtime-файлы разных подсистем.
- Общие `config.py` и `paths.py` формируют скрытую файловую связанность.

Эти связи не переносятся. Они заменяются HTTP `/api/v1`, JSON CLI, contract
tests и локальными конфигурациями каждого сервиса. Общий Python package между
репозиториями не создаётся.
