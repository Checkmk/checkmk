SHELL    := /bin/bash -e
PIPENV   := PIPENV_VENV_IN_PROJECT=true pipenv
PYTEST   := $(PIPENV) run py.test -s -vv
COVERAGE := $(PIPENV) run coverage
BANDIT   := $(PIPENV) run bandit

.PHONY: help pipenv-check test-unit test-unit-coverage-html test-integration \
        test-gui-crawl test-pylint test-packaging test-docker test-bandit \
        test-shellcheck

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
	@echo "test-docker               - Run docker tests"
	@echo "test-format-python        - Test the python formatting"

# This target needs to be phony so it is run every time because only the other
# makefile can determine that there's nothing to be done.
# TODO: Move everything to top level makefile?
.PHONY: ../.venv bandit.ini test-format-python

../.venv:
	$(MAKE) -C .. .venv

pipenv-check: ../.venv
	$(PIPENV) check

test-format-python: ../.venv
# Explicitly specify --style [FILE] to prevent costly searching in parent directories
# for each file specified via command line
#
# Saw some mixed up lines on stdout after adding the --parallel option. Leaving it on
# for the moment to get the performance boost this option brings.
	PYTHON_FILES=$${PYTHON_FILES-$$(./find-python-files)} ; \
	$(PIPENV) run yapf --parallel --style ../.style.yapf --verbose --diff $$PYTHON_FILES \
	    | grep -e "^Reformatting " -e "(reformatted)$$" \
	    | awk '{if ($$1 == "+++") { print "Unformatted: "$$2 } else {print "Checking "$$2"..."}}' ; exit $${PIPESTATUS[0]}

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

bandit.ini:
	echo -e "[bandit]\ntargets: $$(./find-python-files | tr '\n' ',' | sed 's/,$$//')" > bandit.ini

test-bandit: ../.venv bandit.ini
# Currently only care about high severity reported issues. Once this is reached,
# go and enable the medium/low checks.
	$(BANDIT) -c ../bandit.yaml -r -lll --ini bandit.ini $(BANDIT_OUTPUT_ARGS)

test-shellcheck:
	@CMK_DIR="$(realpath ..)" ; \
	ENTERPRISE_DIR="$(realpath ../enterprise)" ; \
	shellcheck \
		$(SHELLCHECK_OUTPUT_ARGS) \
		$$(grep -l '^#!/.*sh' $$CMK_DIR/agents/* $$CMK_DIR/agents/plugins/* $$CMK_DIR/agents/special/* 2>/dev/null) \
		"$$ENTERPRISE_DIR/agents/mk-remote-alert-handler"
