.PHONY: bootstrap doctor doctor-offline inventory-check ai-history-sync test unit bdd build up boot dev down logs status compose-smoke hh-host-proxy-ensure hh-host-proxy-stop ollama-host-proxy-ensure ollama-host-proxy-stop host-bridges-ensure install-autostart uninstall-autostart autostart-status working-db-inventory working-db-dry-run working-db-backup working-db-purge ensure-local-env

PYTHON ?= python3

-include .env
export CORE_PORT WEB_PORT SCORING_PORT

# Re-evaluated in recipes after ensure so generated egress overrides are included.
COMPOSE = docker compose $$($(PYTHON) scripts/host_http_proxy_socket.py compose-files)

bootstrap:
	$(PYTHON) scripts/workspace.py bootstrap

ensure-local-env:
	$(PYTHON) -c "from pathlib import Path; from scripts.workspace import ensure_local_env_files; \
checks=ensure_local_env_files(Path('.').resolve()); \
[print(f'[{c.level}] {c.subject}: {c.message}') for c in checks]; \
raise SystemExit(1 if any(c.level=='ERROR' for c in checks) else 0)"

doctor:
	$(PYTHON) scripts/workspace.py doctor

doctor-offline:
	$(PYTHON) scripts/workspace.py doctor --offline

inventory-check:
	$(PYTHON) scripts/check_inventory.py

ai-history-sync:
	$(PYTHON) scripts/sync_ai_history.py

unit:
	$(PYTHON) -m unittest -v tests.test_workspace tests.test_inventory tests.test_agent_context tests.test_ai_history tests.test_compose_smoke tests.test_host_http_proxy_socket tests.test_ollama_host_socket tests.test_semantic_worker_process tests.test_autostart tests.test_working_db_cleanup

working-db-inventory:
	$(PYTHON) scripts/working_db_cleanup.py inventory

working-db-dry-run:
	$(PYTHON) scripts/working_db_cleanup.py dry-run

working-db-backup:
	$(PYTHON) scripts/working_db_cleanup.py backup

# Requires CONFIRM=1 to actually delete fixture rows (still runs backup first).
working-db-purge:
	@test "$(CONFIRM)" = "1" || (echo "Refusing: set CONFIRM=1 after reviewing dry-run" >&2; exit 2)
	$(PYTHON) scripts/working_db_cleanup.py purge --execute

bdd:
	$(PYTHON) -m unittest -v tests.test_workspace_bdd tests.test_ai_history_bdd

test: unit bdd

build: host-bridges-ensure ensure-local-env
	$(COMPOSE) build core web osint hh scoring automation

hh-host-proxy-ensure:
	$(PYTHON) scripts/host_http_proxy_socket.py ensure

hh-host-proxy-stop:
	$(PYTHON) scripts/host_http_proxy_socket.py stop

ollama-host-proxy-ensure:
	$(PYTHON) scripts/ollama_host_socket.py ensure

ollama-host-proxy-stop:
	$(PYTHON) scripts/ollama_host_socket.py stop

host-bridges-ensure: hh-host-proxy-ensure ollama-host-proxy-ensure

up: host-bridges-ensure ensure-local-env
	$(COMPOSE) up -d --build

# Boot/start without rebuild — used by systemd autostart.
boot: ensure-local-env
	$(PYTHON) scripts/autostart.py boot

dev: host-bridges-ensure ensure-local-env
	$(COMPOSE) up --build

down:
	$(COMPOSE) down
	$(PYTHON) scripts/host_http_proxy_socket.py stop
	$(PYTHON) scripts/ollama_host_socket.py stop

logs:
	$(COMPOSE) logs -f core web scoring scoring-worker hh rabbitmq automation

status:
	@echo "=== compose ps ==="
	@$(COMPOSE) ps -a
	@echo "=== HTTP probes ==="
	@$(PYTHON) scripts/stack_status.py

compose-smoke:
	$(PYTHON) scripts/compose_smoke.py

install-autostart:
	$(PYTHON) $(CURDIR)/scripts/autostart.py install

uninstall-autostart:
	$(PYTHON) $(CURDIR)/scripts/autostart.py uninstall

autostart-status:
	$(PYTHON) scripts/autostart.py status
