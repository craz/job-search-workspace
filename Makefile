.PHONY: bootstrap doctor doctor-offline inventory-check ai-history-sync test unit bdd

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
	$(PYTHON) -m unittest -v tests.test_workspace tests.test_inventory tests.test_agent_context tests.test_ai_history

bdd:
	$(PYTHON) -m unittest -v tests.test_workspace_bdd tests.test_ai_history_bdd

test: unit bdd
