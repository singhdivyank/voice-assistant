.PHONY: install install-dev test lint format run clean help

# Variables
PYTHON := python
PIP := pip
SRC_DIR := src
TEST_DIR := tests

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	$(PIP) install -r requirements.txt

install-dev: install ## Install development dependencies
	$(PIP) install pytest pytest-cov pytest-mock black isort flake8 mypy

test: ## Run tests
	pytest $(TEST_DIR) -v

test-cov: ## Run tests with coverage report
	pytest $(TEST_DIR) --cov=$(SRC_DIR) --cov-report=html --cov-report=term-missing

lint: ## Run linters
	flake8 $(SRC_DIR) $(TEST_DIR) --max-line-length=100
	mypy $(SRC_DIR) --ignore-missing-imports

format: ## Format code with black and isort
	black $(SRC_DIR) $(TEST_DIR)
	isort $(SRC_DIR) $(TEST_DIR)

format-check: ## Check code formatting without making changes
	black $(SRC_DIR) $(TEST_DIR) --check
	isort $(SRC_DIR) $(TEST_DIR) --check-only

run: ## Run the application
	$(PYTHON) -m $(SRC_DIR).app

clean: ## Clean up generated files
	rm -rf __pycache__ .pytest_cache .mypy_cache .coverage htmlcov
	rm -rf $(SRC_DIR)/__pycache__ $(TEST_DIR)/__pycache__
	rm -f prescription.txt voice.mp3
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

setup: install-dev ## Complete setup for development
	cp -n .env.example .env 2>/dev/null || true
	@echo "Setup complete! Don't forget to add your GOOGLE_API_KEY to .env"