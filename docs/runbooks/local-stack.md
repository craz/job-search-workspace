# Local stack — daily operation (R2.5.2)

Canonical operator path for the Job Search Compose product.

## Start / stop

```bash
make up      # host bridges (HH proxy + Ollama) + compose up -d --build
make down    # compose down + stop host bridges
make status  # compose ps + HTTP probes
make logs    # core web scoring scoring-worker hh rabbitmq
```

Do **not** use `docker compose up --no-deps` for normal daily work.

Plain `docker compose -f compose.yaml up` without `make up` skips HH/Ollama
egress overrides and will leave HH (and Scoring→Ollama) degraded on Linux.

## URLs (defaults; override via `.env`)

| Surface | URL |
|--|--|
| Web | http://127.0.0.1:18080/#vacancies |
| Core API | http://127.0.0.1:18000/docs |
| Scoring health | http://127.0.0.1:8090/health/ready |
| HH API | http://127.0.0.1:8092/health/ready |
| Rabbit management | http://127.0.0.1:15673 |

## Topology notes

- **Core / Web / HH / Rabbit / Postgres** — Compose bridge network.
- **Scoring API + worker** — Compose bridge; Core via `http://core:8000`, Rabbit via `rabbitmq:5672`.
- **Ollama** — stays on the host GPU; Compose reaches it through `ollama-egress` (unix-socket relay). Linux bridge containers cannot reliably use `host.docker.internal` for host TCP.
- **HH host HTTP proxy** — same pattern via `hh-egress` (`docs/runbooks/hh-docker-host-proxy.md`).

## Degraded mode

| Dependency down | Vacancy review | Manual «Оценить» | HH search/login |
|--|--|--|--|
| Scoring | works (Core data) | clear error, no crash | unaffected |
| HH | works | may need source-status later | unavailable / degraded ready |
| Core | Web unavailable | unavailable | unavailable |

Restart Scoring alone: review stays up; when healthy again, manual scoring works without restarting Web.

## Manual scoring

1. `make up` (worker starts with `concurrency=1`, consumes only already-published queue work).
2. Open Web → vacancy without current Assessment → **Оценить**.
3. Wait for terminal Assessment (or safe error). Does **not** enqueue the full backlog.

## Startup does not auto-score backlog

`scoring-worker` only processes messages already on Rabbit. No scheduler / no
automatic eligible backlog enqueue on `make up`.
