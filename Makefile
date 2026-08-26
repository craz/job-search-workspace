.PHONY: bootstrap doctor doctor-offline inventory-check ai-history-sync test unit bdd build up dev down logs compose-smoke hh-host-proxy-ensure hh-host-proxy-stop

PYTHON ?= python3

-include .env
export CORE_PORT WEB_PORT

# Re-evaluated in recipes after ensure so the generated HH egress override is included.
COMPOSE = docker compose $$($(PYTHON) scripts/host_http_proxy_socket.py compose-files)

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
	$(PYTHON) -m unittest -v tests.test_workspace tests.test_inventory tests.test_agent_context tests.test_ai_history tests.test_compose_smoke tests.test_host_http_proxy_socket

bdd:
	$(PYTHON) -m unittest -v tests.test_workspace_bdd tests.test_ai_history_bdd

test: unit bdd

build: hh-host-proxy-ensure
	$(COMPOSE) build core web osint hh

hh-host-proxy-ensure:
	$(PYTHON) scripts/host_http_proxy_socket.py ensure

hh-host-proxy-stop:
	$(PYTHON) scripts/host_http_proxy_socket.py stop

up: hh-host-proxy-ensure
	$(COMPOSE) up -d --build

dev: hh-host-proxy-ensure
	$(COMPOSE) up --build

down:
	$(COMPOSE) down
	$(PYTHON) scripts/host_http_proxy_socket.py stop

logs:
	$(COMPOSE) logs -f core web osint searxng hh

compose-smoke:
	$(PYTHON) scripts/compose_smoke.py
