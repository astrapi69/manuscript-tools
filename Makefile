.DEFAULT_GOAL := help
SHELL := /bin/bash

MANUSCRIPT ?= manuscript
INCLUDE    ?= **/*.md
EXCLUDE    ?=

# Build exclude flags dynamically
_EXCLUDE_FLAGS := $(foreach p,$(EXCLUDE),--exclude $(p))

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

.PHONY: lock-install
lock-install: ## Lock and Install project dependencies
	poetry lock
	poetry install

.PHONY: install
install: ## Install project with all dependencies
	poetry install

.PHONY: install-dev
install-dev: ## Install with dev dependencies
	poetry install --with dev

# ---------------------------------------------------------------------------
# Manuscript tasks
# ---------------------------------------------------------------------------

.PHONY: check
check: ## Run core style checks on manuscript
	poetry run ms-check $(MANUSCRIPT) --include '$(INCLUDE)' $(_EXCLUDE_FLAGS)

.PHONY: check-strict
check-strict: ## Run all checks including prose analysis (filler, passive, sentence length)
	poetry run ms-check $(MANUSCRIPT) --include '$(INCLUDE)' $(_EXCLUDE_FLAGS) --strict

.PHONY: sanitize
sanitize: ## Sanitize manuscript files (in-place)
	poetry run ms-sanitize $(MANUSCRIPT) --include '$(INCLUDE)' $(_EXCLUDE_FLAGS)

.PHONY: sanitize-dry
sanitize-dry: ## Sanitize dry-run (show changes without writing)
	poetry run ms-sanitize $(MANUSCRIPT) --include '$(INCLUDE)' $(_EXCLUDE_FLAGS) --dry-run

.PHONY: sanitize-backup
sanitize-backup: ## Sanitize with .bak backup files
	poetry run ms-sanitize $(MANUSCRIPT) --include '$(INCLUDE)' $(_EXCLUDE_FLAGS) --backup

.PHONY: quotes
quotes: ## Fix German quotation marks
	poetry run ms-quotes $(MANUSCRIPT) --include '$(INCLUDE)' $(_EXCLUDE_FLAGS)

.PHONY: quotes-dry
quotes-dry: ## Preview quotation mark fixes
	poetry run ms-quotes $(MANUSCRIPT) --include '$(INCLUDE)' $(_EXCLUDE_FLAGS) --dry-run

.PHONY: format-md
format-md: ## Fix broken bold/italic formatting
	poetry run ms-format $(MANUSCRIPT) --include '$(INCLUDE)' $(_EXCLUDE_FLAGS)

.PHONY: format-md-dry
format-md-dry: ## Preview formatting fixes
	poetry run ms-format $(MANUSCRIPT) --include '$(INCLUDE)' $(_EXCLUDE_FLAGS) --dry-run

.PHONY: metrics
metrics: ## Show word counts, readability and text metrics
	poetry run ms-metrics $(MANUSCRIPT) --include '$(INCLUDE)' $(_EXCLUDE_FLAGS)

.PHONY: validate
validate: ## Full validation pipeline (sanitize + check + readability)
	poetry run ms-validate $(MANUSCRIPT) --include '$(INCLUDE)' $(_EXCLUDE_FLAGS)

.PHONY: validate-fix
validate-fix: ## Full validation with auto-fix (sanitize applied, not dry-run)
	poetry run ms-validate $(MANUSCRIPT) --include '$(INCLUDE)' $(_EXCLUDE_FLAGS) --fix

# ---------------------------------------------------------------------------
# Development
# ---------------------------------------------------------------------------

.PHONY: test
test: ## Run all tests
	poetry run pytest

.PHONY: test-v
test-v: ## Run all tests (verbose)
	poetry run pytest -v

.PHONY: test-cov
test-cov: ## Run tests with coverage report
	poetry run pytest --cov=manuscript_tools --cov-report=term-missing

.PHONY: lint
lint: ## Run ruff linter
	poetry run ruff check src/ tests/

.PHONY: lint-fix
lint-fix: ## Run ruff linter with auto-fix
	poetry run ruff check src/ tests/ --fix

.PHONY: format
format: ## Format code with ruff
	poetry run ruff format src/ tests/

.PHONY: format-check
format-check: ## Check formatting without changes
	poetry run ruff format src/ tests/ --check

.PHONY: ci
ci: lint format-check test ## Full CI pipeline (lint + format-check + test)

# ---------------------------------------------------------------------------
# Version management
# ---------------------------------------------------------------------------

.PHONY: bump-patch
bump-patch: ## Bump patch version (0.2.0 -> 0.2.1)
	python scripts/bump_version.py patch

.PHONY: bump-minor
bump-minor: ## Bump minor version (0.2.0 -> 0.3.0)
	python scripts/bump_version.py minor

.PHONY: bump-major
bump-major: ## Bump major version (0.2.0 -> 1.0.0)
	python scripts/bump_version.py major

# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------

.PHONY: git-setup
git-setup: ## Configure git hooks and commit template
	git config core.hooksPath .githooks
	git config commit.template .gitmessage
	chmod +x .githooks/*
	@echo "Git hooks und commit template aktiviert."

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

.PHONY: clean
clean: ## Remove build artifacts and caches
	rm -rf dist/ .pytest_cache/ .ruff_cache/ .coverage
	find src/ tests/ -type d -name __pycache__ -exec rm -rf {} +
	find . -name '*.pyc' -delete

.PHONY: clean-bak
clean-bak: ## Remove .bak files created by sanitize --backup
	find $(MANUSCRIPT) -name '*.bak' -delete

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

.PHONY: build
build: ## Build distribution package
	poetry build

.PHONY: publish
publish: ci build ## Run CI, build and publish to PyPI
	poetry publish

.PHONY: publish-test
publish-test: ci build ## Run CI, build and publish to TestPyPI
	poetry publish -r testpypi

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ----------------------------------------------------------------------
# Project Releases
# ----------------------------------------------------------------------

.PHONY: tag-message

tag-message: ## Interactive: Generate tag message file and (optionally) create tag
	python scripts/make_tag_message.py
