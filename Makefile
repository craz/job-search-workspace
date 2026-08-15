.PHONY: bootstrap doctor doctor-offline test unit bdd

PYTHON ?= python3

bootstrap:
	$(PYTHON) scripts/workspace.py bootstrap

doctor:
	$(PYTHON) scripts/workspace.py doctor

doctor-offline:
	$(PYTHON) scripts/workspace.py doctor --offline

unit:
	$(PYTHON) -m unittest -v tests.test_workspace

bdd:
	$(PYTHON) -m unittest -v tests.test_workspace_bdd

test: unit bdd
