# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

SHELL := /bin/bash -e
SCRIPTS := ../scripts
FIND_PYTHON_FILES := $(SCRIPTS)/find-python-files
PIPENV3 := $(SCRIPTS)/run-pipenv 3
PYTEST := $(PIPENV3) run py.test -vv
YAPF := $(PIPENV3) run yapf
THREE_TO_TWO := $(PIPENV3) run 3to2
BANDIT := $(PIPENV3) run bandit
MYPY := $(SCRIPTS)/run-mypy
ADDITIONAL_MYPY_ARGS :=

# Since the unit tests (that are written for Python 3) are executed with Python 2.6, we need to
# convert them, just like it is done for the agent plugins (see agents/plugins/Makefile)
AGENT_PLUGIN_UNIT_TEST_FILES := $(wildcard agent-plugin-unit/test_*.py)
AGENT_PLUGIN_UNIT_TEST_FILES_PY26 := $(subst agent-plugin-unit,agent-plugin-unit/py26,$(AGENT_PLUGIN_UNIT_TEST_FILES))

# TODO: Complete this list
SHELL_FILES := \
	agents/check_mk_agent.linux \
	agents/check_mk_caching_agent.linux

.PHONY: clean help format-shell prepare-node-modules test-bandit test-composition \
	test-composition-docker test-composition-docker-debug test-docker test-format-python3 \
	test-format-shell test-gui-crawl test-gui-crawl-docker test-integration \
	test-integration-docker test-integration-docker-debug test-mypy3 test-mypy3-raw \
	test-packaging test-pipenv-deps test-pylint test-shellcheck test-unit test-unit-coverage-html

clean:
	rm -rf .mypy_cache

help:
	@echo "test-agent-plugin-unit-py%-docker - Run Agent plugin tests in container (py version specific)"
	@echo "test-bandit                   - Run bandit (security) tests"
	@echo "test-composition              - Run composition tests locally"
	@echo "test-composition-docker       - Run composition tests in container"
	@echo "test-composition-docker-debug - Run test container for manual debugging"
	@echo "test-docker                   - Run docker tests"
	@echo "test-format-python3           - Run Python 3 formatting tests"
	@echo "test-format-shell             - Run the shell formatting"
	@echo "test-gui-crawl                - Run GUI crawl locally"
	@echo "test-gui-crawl-docker         - Run GUI crawl in container"
	@echo "test-integration              - Run integration tests locally"
	@echo "test-integration-docker       - Run integration tests in container"
	@echo "test-integration-docker-debug - Run test container for manual debugging"
	@echo "test-mypy3                    - Run mypy tests for Python 3"
	@echo "test-mypy3-raw                - Run mypy tests for Python 3 with raw edition config"
	@echo "test-packaging                - Run packaging tests"
	@echo "test-pipenv-deps              - Run pipenv dependency issue test"
	@echo "test-pylint                   - Run pylint based tests"
	@echo "test-shellcheck               - Run shellcheck tests"
	@echo "test-unit                     - Run unit tests"
	@echo "test-unit-coverage-html       - Create HTML coverage report for unit tests"

bandit.ini:
	( echo -n -e "[bandit]\ntargets: "; \
	  $(FIND_PYTHON_FILES) 3 | tr '\n' ',' | sed 's/,$$//'; \
	  echo ) > bandit.ini

format-shell:
	sudo docker run --rm -v "$(realpath ..):/sh" -w /sh peterdavehello/shfmt shfmt -w -i 4 -ci $(SHELL_FILES)

test-agent-plugin-unit-py2.6-docker: $(AGENT_PLUGIN_UNIT_TEST_FILES_PY26)

agent-plugin-unit/py26/test_%.py: agent-plugin-unit/test_%.py
	mkdir -p "$(dir $@)"
	cp "$<" "$@"
	sed -i '0,/^$$/{s/^$$/\n# Do not test generated 2.6 files\n# type: ignore\n&/}' "$@"
	$(THREE_TO_TWO) -x str -n -w "$@" >/dev/null

test-agent-plugin-unit-py%-docker:
	make -C ../agents/plugins
	if [ "$*" = "2.6" ]; then \
	    TEST_PATH="$(realpath agent-plugin-unit)/py26" ; \
	else \
	    TEST_PATH="$(realpath agent-plugin-unit)" ; \
	fi && \
	IMAGE_HASH="$$(docker build --build-arg PYTHON_VERSION="$*" -q "$(realpath agent-plugin-unit)")" && \
	docker run \
	    $(DOCKER_ADDOPTS) \
	    -e "PYTEST_ADDOPTS" \
	    -u $$(id -u):$$(id -g) \
	    -v "$$TEST_PATH:/tests" \
	    -v "$(realpath agent-plugin-unit)/utils.py:/tests/utils.py" \
	    -v "$(realpath agent-plugin-unit)/datasets:/tests/datasets" \
	    -v "$(realpath ../agents/plugins):/plugins" \
	    $$IMAGE_HASH \
	    python$* -m pytest --ignore=tests/py26/ "/tests"

test-bandit: bandit.ini
# Currently only care about high severity reported issues. Once this is reached,
# go and enable the medium/low checks.
	$(BANDIT) -c ../bandit.yaml -r -lll --ini bandit.ini $(BANDIT_OUTPUT_ARGS)

prepare-node-modules:
	$(MAKE) -C .. node_modules/.bin/webpack

test-integration-docker-debug test-composition-docker-debug: prepare-node-modules
	$(PIPENV3) run scripts/run-dockerized.py debug

test-composition-docker:
	$(PIPENV3) run scripts/run-dockerized.py "test-composition"

test-composition: prepare-node-modules
	$(PYTEST) -p no:cov -T composition $(realpath composition)

test-docker:
	$(MAKE) -C ../docker test-lint-dockerfile test-lint-entrypoint
	$(PYTEST) -T docker docker

test-format-python3: ../.style.yapf
# Explicitly specify --style [FILE] to prevent costly searching in parent directories
# for each file specified via command line
#
# There are some mixed up lines on stdout caused by the --parallel option.
# Nevertheless, we keep that option to get a big performance boost. GitHub issue
# opened for this problem: https://github.com/google/yapf/issues/644.
	@if test -z "$$PYTHON_FILES"; then $(FIND_PYTHON_FILES) 3; else echo "$$PYTHON_FILES"; fi | \
	xargs -n 1500 $(YAPF) --parallel --style ../.style.yapf --verbose --diff | \
	grep '^+++ .*(reformatted)$$' | \
	sed -e 's/^+++ //' -e 's/[[:blank:]]*(reformatted)$$/:1:1: error: file needs formatting/' ; \
	exit $${PIPESTATUS[0]}

test-format-shell:
	docker run --rm -v "$(realpath ..):/sh" -w /sh peterdavehello/shfmt shfmt -d -i 4 -ci $(SHELL_FILES)

test-gui-crawl: prepare-node-modules
	$(PYTEST) -T gui_crawl $(realpath gui_crawl/test_gui_crawl.py)

test-gui-crawl-docker:
	$(PIPENV3) run scripts/run-dockerized.py "test-gui-crawl"

test-integration: prepare-node-modules
	CI=true $(PIPENV3) run scripts/run-integration-test.py $(realpath integration)

test-integration-docker:
	$(PIPENV3) run scripts/run-dockerized.py "test-integration"

test-mypy3:
	$(FIND_PYTHON_FILES) 3 | \
	`: filter out plugins, they are not real modules` \
	grep -v $$(realpath '../checks') | \
	grep -v $$(realpath '../inventory') | \
	if test -d ../enterprise; then \
	    grep -v $$(realpath '../agents')/bakery; \
	else \
	    cat; \
	fi | xargs -n 1500 $(MYPY) $(ADDITIONAL_MYPY_ARGS)

test-mypy3-raw:
	$(MAKE) test-mypy3 ADDITIONAL_MYPY_ARGS="--config-file=$(realpath ../mypy-raw.ini)"

test-packaging:
	$(PYTEST) -T packaging packaging

test-pipenv-deps:
	$(PIPENV3) check

test-pylint:
	$(PYTEST) -T pylint pylint

test-shellcheck:
	@CMK_DIR="$(realpath ..)" ; \
	ENTERPRISE_DIR="$(realpath ../enterprise)" ; \
	shellcheck \
		$(SHELLCHECK_OUTPUT_ARGS) \
		$$(grep -l '^#!/.*sh' $$CMK_DIR/agents/* $$CMK_DIR/agents/plugins/* $$CMK_DIR/agents/special/* 2>/dev/null) \
		"$$ENTERPRISE_DIR/agents/mk-remote-alert-handler"

test-unit:
	$(PYTEST) -T unit unit

test-unit-coverage-html:
	$(PYTEST) \
	    --cov=cmk \
	    --cov-report=html \
	    --cov-config=.coveragerc_unit \
	    --no-cov-on-fail \
	    -T unit unit
