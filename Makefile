.PHONY: bootstrap doctor doctor-offline inventory-check test unit bdd

PYTHON ?= python3

bootstrap:
	$(PYTHON) scripts/workspace.py bootstrap

doctor:
	$(PYTHON) scripts/workspace.py doctor

doctor-offline:
	$(PYTHON) scripts/workspace.py doctor --offline

inventory-check:
	$(PYTHON) scripts/check_inventory.py

unit:
	$(PYTHON) -m unittest -v tests.test_workspace tests.test_inventory tests.test_agent_context

bdd:
	$(PYTHON) -m unittest -v tests.test_workspace_bdd

test: unit bdd
