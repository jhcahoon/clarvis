# Clarvis Makefile
# Commands for development, testing, and evaluation

.PHONY: help install test lint eval-routing eval-edge eval-follow eval-all eval-view

# Default target
help:
	@echo "Clarvis Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  install      Install dependencies with uv"
	@echo ""
	@echo "Testing:"
	@echo "  test         Run all tests with pytest"
	@echo "  test-cov     Run tests with coverage report"
	@echo "  lint         Run linting with ruff"
	@echo ""
	@echo "Routing Evaluation (Promptfoo):"
	@echo "  eval-routing Run core routing tests"
	@echo "  eval-edge    Run edge case tests"
	@echo "  eval-follow  Run follow-up detection tests"
	@echo "  eval-all     Run all evaluation suites"
	@echo "  eval-view    Launch promptfoo web viewer"
	@echo ""
	@echo "Server:"
	@echo "  serve        Run the API server"
	@echo "  serve-dev    Run the API server with auto-reload"

# Setup
install:
	uv sync

# Testing
test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=clarvis_agents --cov-report=term-missing

lint:
	ruff check clarvis_agents/
	black --check clarvis_agents/

# Routing Evaluation with Promptfoo
eval-routing:
	npx promptfoo eval -c evals/routing_eval.yaml

eval-edge:
	npx promptfoo eval -c evals/edge_cases.yaml

eval-follow:
	npx promptfoo eval -c evals/follow_up.yaml

eval-all:
	npx promptfoo eval -c evals/routing_eval.yaml -c evals/edge_cases.yaml -c evals/follow_up.yaml

eval-view:
	npx promptfoo view

# Server
serve:
	python scripts/run_api_server.py

serve-dev:
	python scripts/run_api_server.py --reload
