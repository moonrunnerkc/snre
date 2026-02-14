.PHONY: help install test lint format clean docs contract-check

# Default target
help:
	@echo "SNRE - Swarm Neural Refactoring Engine"
	@echo ""
	@echo "Available targets:"
	@echo "  install       Install dependencies and setup environment"
	@echo "  test          Run all tests"
	@echo "  lint          Run linting and type checking" 
	@echo "  format        Format code with ruff"
	@echo "  contract-check Validate contract compliance"
	@echo "  clean         Clean build artifacts and cache"
	@echo "  docs          Generate documentation"
	@echo "  run-cli       Start CLI interface"
	@echo "  run-api       Start API server"

# Installation and setup
install:
	python -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt
	mkdir -p data/refactor_logs data/snapshots logs

install-dev: install
	./venv/bin/pip install pytest pytest-cov ruff mypy black bandit

# Testing
test:
	pytest tests/ -v --cov=. --cov-report=term --cov-report=html

test-integration:
	pytest tests/ -v -m integration

test-fast:
	pytest tests/ -v -x --tb=short

# Code quality
lint: 
	ruff check .
	mypy . --ignore-missing-imports --follow-imports=silent

format:
	ruff format .
	ruff check . --fix

contract-check:
	python scripts/check_contract.py

security-scan:
	bandit -r . -f json -o security-report.json

# Running the application
run-cli:
	python main.py cli --help

run-api:
	python main.py api localhost 8000

run-example:
	echo "def inefficient_loop():\n    result = []\n    for i in range(len(items)):\n        result.append(items[i] * 2)\n    return result" > example.py
	python main.py cli validate --path example.py

# Development utilities
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf build/ dist/ *.egg-info/
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf data/refactor_logs/* data/snapshots/*

docs:
	@echo "Documentation available in docs/architecture.md"
	@echo "API specification in API_SPEC.md"

# CI pipeline simulation
ci: clean contract-check lint test security-scan
	@echo "✅ All CI checks passed"

# Development workflow
dev-setup: install-dev
	@echo "Development environment ready"
	@echo "Run 'make test' to verify installation"

# Quick validation
check: contract-check lint
	@echo "✅ Contract and code quality checks passed"

# Release preparation
release-check: clean ci docs
	@echo "✅ Release validation complete"