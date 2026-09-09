# Local stack — daily operation (R2.5.2 + R2.5.3 / R2.5.3A + PB-REL-00)

Canonical operator path for the Job Search Compose product.

## First-time clean install

Prerequisites: Linux, Git, Docker (daemon + Compose plugin), Python 3.12+, Make.  
Optional: `direnv`, host Ollama + scoring model, HH OAuth client id/secret.

```bash
git clone --recurse-submodules https://github.com/craz/job-search-workspace.git
cd job-search-workspace
make bootstrap    # locked submodule gitlinks + .env / services/hh/.env from examples
make doctor       # or: make doctor-offline
make up           # host bridges + compose up -d --build
make status
```

Open Web: http://127.0.0.1:8080/ (or `WEB_PORT` from `.env`).

Core runs `alembic upgrade head` on every container start against an empty volume —
schema reaches HEAD without manual migration commands. A second `make up` / Core
restart is idempotent (no duplicate seed rows beyond the single active SearchCycle).

Do **not** copy production DB dumps, `.local/`, or personal HH cookies into a clean install.

## Configuration contract

| Kind | Where | Notes |
|--|--|--|
| **REQUIRED (base)** | Compose defaults + `.env.example` → `.env` | Ports only; product starts with defaults |
| **REQUIRED (HH file)** | `services/hh/.env.example` → `services/hh/.env` | File must exist for Compose `env_file`; empty OAuth fields OK |
| **OPTIONAL** | HH OAuth id/secret, host HTTP proxy, Ollama model | Integrations degrade cleanly when absent |
| **PRIVATE** | Real tokens, cookies, browser profile, PSP values, DB dumps | Never commit; stay in `.env` / volumes / `.local/` |

`make ensure-local-env` / `make bootstrap` create missing env files from examples and **never overwrite** existing ones.

## Start / stop

```bash
make up      # host bridges (HH proxy + Ollama) + compose up -d --build
make boot    # same bridges + remount egress + compose up -d (no rebuild; machine boot)
make restart # supported full restart: bridges + remount egress + compose up
make down    # compose down + stop host bridges
make status  # compose ps + HTTP probes
make logs    # core web scoring scoring-worker hh rabbitmq automation
make doctor  # tools, submodule gitlinks, env presence, optional remotes
```

Do **not** use `docker compose up --no-deps` for normal daily work.

Do **not** use plain `docker compose restart` as the normal restart path: it leaves
host unix-socket bridges / egress mounts untouched and can keep HH browser egress
broken while containers still look “Up”.

Plain `docker compose -f compose.yaml up` without `make up`/`make boot` skips HH/Ollama
egress overrides and will leave HH (and Scoring→Ollama) degraded on Linux.

## Machine boot autostart (R2.5.3A)

Docker Compose restart policies alone are **not** enough: boot must recreate host
unix-socket bridges (`hh-egress` / `ollama-egress`) before Compose attaches.

One-time setup (prefers system unit with sudo; falls back to user unit):

```bash
make install-autostart          # or: sudo make install-autostart
make autostart-status
# if user unit + headless boot without login:
# sudo loginctl enable-linger "$USER"
```

Disable:

```bash
make uninstall-autostart        # use sudo if the system unit was installed
```

Unit: `job-search.service` → `make boot` after Docker is ready.

## URLs (defaults; override via `.env`)

| Surface | URL |
|--|--|
| Web | http://127.0.0.1:8080/ (example override `WEB_PORT=18080` → :18080) |
| Core API | http://127.0.0.1:8000/docs |
| Scoring health | http://127.0.0.1:8090/health/ready |
| HH API | http://127.0.0.1:8092/health/ready |
| Automation | http://127.0.0.1:8095/api/v1/automation/status |
| Rabbit management | http://127.0.0.1:15673 |

## Topology notes

- **Core / Web / HH / Rabbit / Postgres / Automation** — Compose bridge network.
- **Scoring API + worker** — Compose bridge; Core via `http://core:8000`, Rabbit via `rabbitmq:5672`.
- **Ollama** — stays on the host GPU; Compose reaches it through `ollama-egress` (unix-socket relay).
- **HH host HTTP proxy** — same pattern via `hh-egress`.

## Automation (PB-AUTO-00 / R2.5.3)

One Compose service `automation` runs a simple interval loop (default **60 minutes**).

Each cycle: active HH resume → `resume_suitable` acquisition → Core ingest/dedupe →
enqueue semantic scoring **only** for `created`/`updated` items from **this** SearchRun
(bounded by `AUTO_SCORING_MAX_PER_CYCLE`, default 20) → existing `scoring-worker` does inference.

| Control | How |
|--|--|
| Enable / disable | Web → блок «Автоматизация», or `POST /api/v1/automation/enable` |
| Run now | Web button or `POST /api/v1/automation/run-now` |
| Status | Web panel / `make status` / automation status API |

**Default after deploy: DISABLED** (`AUTOMATION_ENABLED=0`). Enabling does **not** fire
immediately — it schedules the next run; use **Run now** for a controlled cycle.

`enabled` is persisted on the `automation-state` volume and survives Compose/machine reboot.

Does **not** automate: applications, recruiter messages, OSINT, historical backlog scoring,
owner_decision changes.

## Degraded mode

| Dependency down | Vacancy review | Manual «Оценить» | HH search/login | Automation |
|--|--|--|--|--|
| Scoring | works (Core data) | clear error | unaffected | cycle errors, lock released |
| HH | works | may need source-status | unavailable | cycle errors / user action |
| Automation | works | works | works | controls unavailable |
| Core | Web unavailable | unavailable | unavailable | unavailable |

## Manual scoring

1. `make up` (worker starts with `concurrency=1`, consumes only already-published queue work).
2. Open Web → vacancy without current Assessment → **Оценить**.
3. Wait for terminal Assessment (or safe error). Does **not** enqueue the full backlog.

## Startup does not auto-score backlog

`scoring-worker` only processes messages already on Rabbit. Automation (when enabled)
enqueues only current-cycle eligible vacancies, never `SELECT all never_scored`.

## Working DB cleanup

See [`docs/PB_DATA_01_WORKING_DB_CLEANUP.md`](../PB_DATA_01_WORKING_DB_CLEANUP.md) for
inventory / dry-run / purge of provable fixture rows (never commit dumps).
