.PHONY: bootstrap doctor doctor-offline inventory-check ai-history-sync test unit bdd build up dev down logs status compose-smoke hh-host-proxy-ensure hh-host-proxy-stop ollama-host-proxy-ensure ollama-host-proxy-stop host-bridges-ensure

PYTHON ?= python3

-include .env
export CORE_PORT WEB_PORT SCORING_PORT

# Re-evaluated in recipes after ensure so generated egress overrides are included.
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
	$(PYTHON) -m unittest -v tests.test_workspace tests.test_inventory tests.test_agent_context tests.test_ai_history tests.test_compose_smoke tests.test_host_http_proxy_socket tests.test_ollama_host_socket tests.test_semantic_worker_process

bdd:
	$(PYTHON) -m unittest -v tests.test_workspace_bdd tests.test_ai_history_bdd

test: unit bdd

build: host-bridges-ensure
	$(COMPOSE) build core web osint hh scoring

hh-host-proxy-ensure:
	$(PYTHON) scripts/host_http_proxy_socket.py ensure

hh-host-proxy-stop:
	$(PYTHON) scripts/host_http_proxy_socket.py stop

ollama-host-proxy-ensure:
	$(PYTHON) scripts/ollama_host_socket.py ensure

ollama-host-proxy-stop:
	$(PYTHON) scripts/ollama_host_socket.py stop

host-bridges-ensure: hh-host-proxy-ensure ollama-host-proxy-ensure

up: host-bridges-ensure
	$(COMPOSE) up -d --build

dev: host-bridges-ensure
	$(COMPOSE) up --build

down:
	$(COMPOSE) down
	$(PYTHON) scripts/host_http_proxy_socket.py stop
	$(PYTHON) scripts/ollama_host_socket.py stop

logs:
	$(COMPOSE) logs -f core web scoring scoring-worker hh rabbitmq

status:
	@echo "=== compose ps ==="
	@$(COMPOSE) ps -a
	@echo "=== HTTP probes ==="
	@$(PYTHON) scripts/stack_status.py

compose-smoke:
	$(PYTHON) scripts/compose_smoke.py
