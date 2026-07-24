# ─────────────────────────────────────────────────────────────────────────────
# CloudScale Commerce — Root Makefile
# ─────────────────────────────────────────────────────────────────────────────
# Provides a single entry point for setup, testing, linting, formatting, and
# running the local Docker Compose stack.
#
# Usage:
#   make setup      — Install all Python dependencies (shared + services)
#   make test       — Run all service test suites
#   make lint       — Run ruff linter across the codebase
#   make format     — Run ruff formatter across the codebase
#   make docker-up  — Start the full stack via Docker Compose
# ─────────────────────────────────────────────────────────────────────────────

SHELL := /bin/bash
PYTHON ?= python
PIP ?= pip
PYTEST_OPTS ?= -p no:phoenix -x -q
SERVICES := auth catalog inventory notification order payment

.PHONY: setup test lint format docker-up clean help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── Setup ────────────────────────────────────────────────────────────────────

setup: ## Install shared library and all service dependencies
	$(PIP) install -e shared/python
	@for svc in $(SERVICES); do \
		echo "──── Installing $$svc dependencies ────"; \
		$(PIP) install -r services/$$svc/requirements.txt; \
	done

# ── Testing ──────────────────────────────────────────────────────────────────
# Required env vars are exported automatically so tests pass on clean checkouts.

export JWT_SECRET_KEY ?= test-secret-key-for-ci-only-32chars
export STRIPE_WEBHOOK_SECRET ?= whsec_test_secret
export OTEL_SDK_DISABLED ?= true

test: ## Run pytest for all services
	@failures=0; \
	for svc in $(SERVICES); do \
		echo ""; \
		echo "════════════════════════════════════════════════════════"; \
		echo "  Testing: $$svc"; \
		echo "════════════════════════════════════════════════════════"; \
		PYTHONPATH="services/$$svc" $(PYTHON) -m pytest services/$$svc/tests/ $(PYTEST_OPTS) || failures=$$((failures + 1)); \
	done; \
	echo ""; \
	if [ $$failures -gt 0 ]; then \
		echo "⚠  $$failures service(s) had test failures."; \
		exit 1; \
	else \
		echo "✅ All service tests passed."; \
	fi

test-%: ## Run tests for a single service, e.g. make test-auth
	PYTHONPATH="services/$*" $(PYTHON) -m pytest services/$*/tests/ $(PYTEST_OPTS) -v

# ── Linting & Formatting ────────────────────────────────────────────────────

lint: ## Run ruff linter on all source code
	$(PYTHON) -m ruff check shared/ services/ tests/ --fix

format: ## Run ruff formatter on all source code
	$(PYTHON) -m ruff format shared/ services/ tests/

# ── Docker ───────────────────────────────────────────────────────────────────

docker-up: ## Start full stack via Docker Compose
	docker compose -f deployments/docker/docker-compose.yml up --build -d

docker-down: ## Stop the Docker Compose stack
	docker compose -f deployments/docker/docker-compose.yml down

# ── Cleanup ──────────────────────────────────────────────────────────────────

clean: ## Remove Python caches and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
