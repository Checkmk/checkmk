SHELL    := /bin/bash -e
VENV     := ../.venv
PIPENV   := PIPENV_VENV_IN_PROJECT=true pipenv
BANDIT   := $(PIPENV) run bandit
COVERAGE := $(PIPENV) run coverage
PYTEST   := $(PIPENV) run py.test -s -vv
YAPF     := $(PIPENV) run yapf

.PHONY: help pipenv-check test-bandit test-docker test-format-python \
        test-gui-crawl test-integration test-packaging test-pylint \
        test-shellcheck test-unit test-unit-coverage-html

help:
	echo $(MAKE) -C $(dir $(VENV)) $(notdir $(VENV))
	@echo "pipenv-check              - Checks for security vulnerabilities/PEP 508 markers"
	@echo "test-bandit               - Run bandit (security) tests"
	@echo "test-docker               - Run docker tests"
	@echo "test-format-python        - Test the python formatting"
	@echo "test-gui-crawl            - Run GUI crawl test"
	@echo "test-integration          - Run integration tests"
	@echo "test-packaging            - Run packaging tests"
	@echo "test-pylint               - Run pylint based tests"
	@echo "test-shellcheck           - Run shellcheck tests"
	@echo "test-unit                 - Run unit tests"
	@echo "test-unit-coverage-html   - Create HTML coverage report for unit tests"

# These target need to be phony so it is run every time because only the other
# makefile can determine that there's nothing to be done.
# TODO: Move everything to top level makefile?
.PHONY: $(VENV) bandit.ini

$(VENV):
	$(MAKE) -C $(dir $(VENV)) $(notdir $(VENV))

bandit.ini:
	echo -e "[bandit]\ntargets: $$(./find-python-files | tr '\n' ',' | sed 's/,$$//')" > bandit.ini

pipenv-check: $(VENV)
	$(PIPENV) check

test-bandit: $(VENV) bandit.ini
# Currently only care about high severity reported issues. Once this is reached,
# go and enable the medium/low checks.
	$(BANDIT) -c ../bandit.yaml -r -lll --ini bandit.ini $(BANDIT_OUTPUT_ARGS)

test-docker: $(VENV)
	$(MAKE) -C ../docker test-lint-dockerfile test-lint-entrypoint
	$(PYTEST) -T docker

test-format-python: $(VENV) ../.style.yapf
# Explicitly specify --style [FILE] to prevent costly searching in parent directories
# for each file specified via command line
#
# There are some mixed up lines on stdout caused by the --parallel option.
# Nevertheless, we keep that option to get a big performance boost. GitHub issue
# opened for this problem: https://github.com/google/yapf/issues/644.
	PYTHON_FILES=$${PYTHON_FILES-$$(./find-python-files)} ; \
	$(YAPF) --parallel --style ../.style.yapf --verbose --diff $$PYTHON_FILES | \
		grep '^+++ .*(reformatted)$$' | \
		sed -e 's/^+++ //' -e 's/[[:blank:]]*(reformatted)$$/:1:1: error: file needs formatting/'

test-gui-crawl: $(VENV)
	$(PYTEST) -T gui_crawl

test-integration: $(VENV)
	$(PYTEST) -T integration

test-packaging: $(VENV)
	$(PYTEST) -T packaging

test-pylint: $(VENV)
	$(PYTEST) -T pylint

test-shellcheck:
	@CMK_DIR="$(realpath ..)" ; \
	ENTERPRISE_DIR="$(realpath ../enterprise)" ; \
	shellcheck \
		$(SHELLCHECK_OUTPUT_ARGS) \
		$$(grep -l '^#!/.*sh' $$CMK_DIR/agents/* $$CMK_DIR/agents/plugins/* $$CMK_DIR/agents/special/* 2>/dev/null) \
		"$$ENTERPRISE_DIR/agents/mk-remote-alert-handler"

test-unit: $(VENV)
	$(PYTEST) -T unit

test-unit-coverage-html: $(VENV)
	$(COVERAGE) run --rcfile=.coveragerc_unit -m pytest -T unit ; $(COVERAGE) html
