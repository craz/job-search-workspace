.PHONY: bootstrap doctor doctor-offline inventory-check ai-history-sync test unit bdd build dev down logs compose-smoke migration-dry-run migration-apply

PYTHON ?= python3
CORE_VENV := services/core/.venv/bin/python
CORE_PYTHONPATH := PYTHONPATH=.:services/core/src

-include .env
export CORE_PORT WEB_PORT

bootstrap:
	$(PYTHON) scripts/workspace.py bootstrap

doctor:
	$(PYTHON) scripts/workspace.py doctor

doctor-offline:
	$(PYTHON) scripts/workspace.py doctor --offline

inventory-check:
	$(PYTHON) scripts/check_inventory.py

ai-history-sync:
	$(PYTHON) scripts/sync_ai_history.py

unit:
	$(PYTHON) -m unittest -v tests.test_workspace tests.test_inventory tests.test_agent_context tests.test_ai_history tests.test_compose_smoke
	$(CORE_PYTHONPATH) $(CORE_VENV) -m unittest -v tests.test_migration_dry_run

bdd:
	$(PYTHON) -m unittest -v tests.test_workspace_bdd tests.test_ai_history_bdd

test: unit bdd

build:
	docker compose build core web osint

dev:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f core web osint searxng

compose-smoke:
	$(PYTHON) scripts/compose_smoke.py

migration-dry-run:
	$(CORE_PYTHONPATH) $(CORE_VENV) -m scripts.migration dry-run

migration-apply:
	@test -n "$(RUN_ID)" || (echo "RUN_ID is required, e.g. make migration-apply RUN_ID=migrate-YYYYMMDD-HHMMSS-sha" >&2; exit 2)
	$(CORE_PYTHONPATH) $(CORE_VENV) -m scripts.migration apply --run-id $(RUN_ID)
