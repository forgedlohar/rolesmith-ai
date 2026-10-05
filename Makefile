.PHONY: help setup format lint test check run

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Install uv, lock, sync, and playwright
	uv lock
	uv sync
	uv run playwright install

format: ## Format code with ruff
	uv run ruff check --fix .
	uv run ruff format .

lint: ## Lint code with ruff and mypy
	uv run ruff check .
	uv run mypy src tests

test: ## Run tests with pytest
	uv run pytest --cov=rolesmith_ai tests

check: format lint test ## Run format, lint, and test

run: ## Run the MCP server locally over stdio
	uv run rolesmith_ai-mcp

dashboard: ## Run the local dashboard UI
	uv run rolesmith_ai-dashboard

check-emails: ## Scan Gmail for job replies and auto-draft responses
	uv run rolesmith_ai check-emails

follow-ups: ## Draft follow-up emails for old applications
	uv run rolesmith_ai follow-up
