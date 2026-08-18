.PHONY: bootstrap doctor doctor-offline inventory-check ai-history-sync test unit bdd build dev down logs compose-smoke

PYTHON ?= python3

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

bdd:
	$(PYTHON) -m unittest -v tests.test_workspace_bdd tests.test_ai_history_bdd

test: unit bdd

build:
	docker compose build core web

dev:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f core web

compose-smoke:
	$(PYTHON) scripts/compose_smoke.py
