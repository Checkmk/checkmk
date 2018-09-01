SHELL    := /bin/bash -e
PIPENV   := PIPENV_VENV_IN_PROJECT=true pipenv
PYTEST   := $(PIPENV) run py.test -s -vv
COVERAGE := $(PIPENV) run coverage

.PHONY: help test-unit test-unit-coverage-html test-integration test-gui-crawl \
        test-pylint test-packaging test-bandit test-shellcheck

help:
	@echo "setup                     - Install dependencies"
	@echo "test-unit                 - Run unit tests"
	@echo "test-unit-coverage-html   - Create HTML coverage report for unit tests"
	@echo "test-integration          - Run integration tests"
	@echo "test-gui-crawl            - Run GUI crawl test"
	@echo "test-pylint               - Run pylint based tests"
	@echo "test-packaging            - Run packaging tests"
	@echo "test-bandit               - Run bandit (security) tests"
	@echo "test-shellcheck           - Run shellcheck tests"

# This target needs to be phony so it is run every time because only the other
# makefile can determine that there's nothing to be done.
# TODO: Move everything to top level makefile?
.PHONY: ../.venv

../.venv:
	$(MAKE) -C .. .venv

test-unit: ../.venv
	$(PYTEST) -T unit

test-unit-coverage-html: ../.venv
	$(COVERAGE) run --rcfile=.coveragerc_unit -m pytest -T unit ; $(COVERAGE) html

test-integration: ../.venv
	$(PYTEST) -T integration

test-gui-crawl: ../.venv
	$(PYTEST) -T gui_crawl

test-pylint: ../.venv
	$(PYTEST) -T pylint

test-packaging: ../.venv
	$(PYTEST) -T packaging

test-docker: ../.venv
	$(MAKE) -C ../docker test-lint-dockerfile test-lint-entrypoint
	$(PYTEST) -T docker

test-bandit: ../.venv
# Currently only care about high severity reported issues. Once this is reached,
# go and enable the medium/low checks.
	CMK_DIR="$(realpath ..)" ; \
	ENTERPRISE_DIR="$(realpath ../enterprise)" ; \
	bandit \
		-c "$$CMK_DIR/bandit.yaml" \
		-r \
		-lll \
		$(BANDIT_OUTPUT_ARGS) \
		"$$CMK_DIR" \
		$$(grep -l python "$$CMK_DIR"/bin/*) \
		"$$CMK_DIR"/{checks,inventory}/* \
		$$(grep -l python "$$ENTERPRISE_DIR"/bin/*) \
		"$$ENTERPRISE_DIR"/agents/plugins/*.py \
		"$$ENTERPRISE_DIR"/agents/bakery/*

test-shellcheck:
	@CMK_DIR="$(realpath ..)" ; \
	ENTERPRISE_DIR="$(realpath ../enterprise)" ; \
	shellcheck \
		$(SHELLCHECK_OUTPUT_ARGS) \
		$$(grep -l '^#!/.*sh' $$CMK_DIR/agents/* $$CMK_DIR/agents/plugins/* $$CMK_DIR/agents/special/* 2>/dev/null) \
		"$$ENTERPRISE_DIR/agents/mk-remote-alert-handler"
