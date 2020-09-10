# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

SHELL := /bin/bash -e
SCRIPTS := ../scripts
FIND_PYTHON_FILES := $(SCRIPTS)/find-python-files
PIPENV := $(SCRIPTS)/run-pipenv
PYTEST := $(PIPENV) run py.test -vv $(PYTEST_ARGS)
YAPF := $(PIPENV) run yapf
THREE_TO_TWO := $(PIPENV) run 3to2
BANDIT := $(PIPENV) run bandit
FIND_INVALID_TEST_FILES := $(SCRIPTS)/find-invalid-autogen-files
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

PYTHON_VERSIONS := 2.6 2.7 3.3 3.4 3.5 3.6 3.7 3.8

 # Optionally forward the job result to a result file when executed via CI
REDIRECT =
ifdef RESULTS
REDIRECT = &>
CPPCHECK = cppcheck-xml
else
REDIRECT = \#
CPPCHECK = cppcheck
endif

.PHONY: clean format-shell help prepare-node-modules \
	$(foreach VERS,$(PYTHON_VERSIONS),test-agent-plugin-unit-py$(VERS)-docker) \
	test-bandit test-composition test-composition-docker test-composition-docker-debug \
	test-docker test-format-python test-format-python-docker test-format-shell \
        test-gui-crawl test-gui-crawl-docker test-integration test-integration-docker \
        test-integration-docker-debug test-mypy test-mypy-raw itest-mypy-docker \
        test-packaging test-pipenv-deps test-pylint test-pylint-docker test-shellcheck \
        test-unit test-unit-docker test-unit-coverage-html test-unit-sh test-unit-sh-docker \
        test-cppcheck-livestatus test-cppcheck-core test-cppcheck-docker test-tidy-livestatus \
        test-tidy-core test-tidy-docker test-iwyu-livestatus test-iwyu-core test-iwyu-docker \
	test-unit-livestatus test-unit-core %-livestatus-docker %-core-docker

clean:
	$(RM) -r .mypy_cache $(AGENT_PLUGIN_UNIT_TEST_FILES_PY26)

help:
	@echo "format-shell                        - Format shell agents"
	@for i in $(PYTHON_VERSIONS); do \
	    echo "test-agent-plugin-unit-py$${i}-docker - Run Agent plugin tests in container with Python $${i}"; \
	done
	@echo "test-bandit                         - Run bandit (security) tests"
	@echo "test-composition                    - Run composition tests locally"
	@echo "test-composition-docker             - Run composition tests in container"
	@echo "test-composition-docker-debug       - Run test container for manual debugging"
	@echo "test-docker                         - Run docker tests"
	@echo "test-format-python                  - Run formatting tests"
	@echo "test-format-python-docker           - Run formatting tests in docker"
	@echo "test-format-shell                   - Run the shell formatting"
	@echo "test-gui-crawl                      - Run GUI crawl locally"
	@echo "test-gui-crawl-docker               - Run GUI crawl in container"
	@echo "test-integration                    - Run integration tests locally"
	@echo "test-integration-docker             - Run integration tests in container"
	@echo "test-integration-docker-debug       - Run test container for manual debugging"
	@echo "test-mypy                           - Run mypy"
	@echo "test-mypy-raw                       - Run mypy with raw edition config"
	@echo "test-mypy-docker                    - Run mypy in docker"
	@echo "test-packaging                      - Run packaging tests"
	@echo "test-pipenv-deps                    - Run pipenv dependency issue test"
	@echo "test-pylint                         - Run pylint based tests"
	@echo "test-shellcheck                     - Run shellcheck tests"
	@echo "test-unit                           - Run unit tests"
	@echo "test-unit-docker                    - Run unit tests in docker"
	@echo "test-unit-coverage-html             - Create HTML coverage report for unit tests"
	@echo "test-unit-sh		           - Run shell unit tests"
	@echo "test-unit-sh-docker	           - Run shell unit tests in docker"
	@echo "test-cppcheck-livestatus            - Run cppcheck for livestatus"
	@echo "test-cppcheck-core                  - Run cppcheck for the core"
	@echo "test-cppcheck-docker                - Run both cppcheck in docker"
	@echo "test-tidy-livestatus                - Run clang tidy for livestatus"
	@echo "test-tidy-core                      - Run clang tidy for core"
	@echo "test-tidy-docker                    - Run clang tidy for core and livestatus in docker"
	@echo "test-iwyu-livestatus                - Run the iwyu tool for livestatus"
	@echo "test-iwyu-core                      - Run the iwyu tool for the core"
	@echo "test-iwyu-docker                    - Run the iwyu tool for both in docker"
	@echo "test-unit-livestatus                - Run unit tests for livestatus"
	@echo "test-unit-core                      - Run unit tests for core"
	@echo "*-livestatus-docker                 - Run any of the livestatus tests in docker"
	@echo "*-core-docker                       - Run any of the core tests in docker"

bandit.ini:
	( echo -n -e "[bandit]\ntargets: "; \
	  $(FIND_PYTHON_FILES) | tr '\n' ',' | sed 's/,$$//'; \
	  echo ) > bandit.ini

format-shell:
	sudo docker run --rm -v "$(realpath ..):/sh" -w /sh peterdavehello/shfmt shfmt -w -i 4 -ci $(SHELL_FILES)

agent-plugin-unit/py26/test_%.py: agent-plugin-unit/test_%.py
	mkdir -p "$(dir $@)"
	cat "$<" | gawk -v text="# Do not test generated 2.6 files\n# yapf: disable\n# type: ignore" '!/^#/ && !p {print text; p=1} 1' > "$@"
	$(THREE_TO_TWO) --nofix=str --nobackups --write "$@" >/dev/null

$(foreach VERS,$(filter 2.%,$(PYTHON_VERSIONS)),test-agent-plugin-unit-py$(VERS)-docker): $(AGENT_PLUGIN_UNIT_TEST_FILES_PY26)

$(foreach VERS,$(PYTHON_VERSIONS),test-agent-plugin-unit-py$(VERS)-docker):
	# Clean up auto-generated files, which do not have a corresponding source file anymore
	flock ./agent-plugin-unit $(FIND_INVALID_TEST_FILES)
	# Recursive Makefiles suck big time...
	flock ../agents/plugins $(MAKE) -C ../agents/plugins
	PYTHON_VERSION="$(patsubst test-agent-plugin-unit-py%-docker,%,$@)" ; \
	case $$PYTHON_VERSION in \
	    2.*) SUFFIX="/py26" ;; \
	    *) SUFFIX="" ;; \
	esac ; \
	TEST_PATH="$(realpath agent-plugin-unit)$$SUFFIX" ; \
	IMAGE_HASH="$$(docker build --build-arg PYTHON_VERSION="$$PYTHON_VERSION" -q "$(realpath agent-plugin-unit)")" && \
	docker run \
	    $(DOCKER_ADDOPTS) \
	    -e "PYTEST_ADDOPTS" \
	    -u $$(id -u):$$(id -g) \
	    -v "$$TEST_PATH:/tests" \
	    -v "$(realpath agent-plugin-unit)/utils.py:/tests/utils.py" \
	    -v "$(realpath agent-plugin-unit)/datasets:/tests/datasets" \
	    -v "$(realpath ../agents/plugins):/plugins" \
	    $$IMAGE_HASH \
	    python$$PYTHON_VERSION -m pytest --ignore=tests/py26/ "/tests"

test-bandit: bandit.ini
# Currently only care about high severity reported issues. Once this is reached,
# go and enable the medium/low checks.
	$(BANDIT) -c ../bandit.yaml -r -lll --ini bandit.ini $(BANDIT_OUTPUT_ARGS)

prepare-node-modules:
	$(MAKE) -C .. node_modules/.bin/webpack

test-integration-docker-debug test-composition-docker-debug: prepare-node-modules
	$(PIPENV) run scripts/run-dockerized.py debug

test-composition-docker:
	$(PIPENV) run scripts/run-dockerized.py "test-composition"

test-composition: prepare-node-modules
	$(PYTEST) -p no:cov -T composition $(realpath composition)

test-docker:
	$(MAKE) -C ../docker test-lint-dockerfile test-lint-entrypoint
	$(PYTEST) -T docker docker

test-format-python: ../.style.yapf
# Explicitly specify --style [FILE] to prevent costly searching in parent directories
# for each file specified via command line
#
# There are some mixed up lines on stdout caused by the --parallel option.
# Nevertheless, we keep that option to get a big performance boost. GitHub issue
# opened for this problem: https://github.com/google/yapf/issues/644.
	@if test -z "$$PYTHON_FILES"; then $(FIND_PYTHON_FILES); else echo "$$PYTHON_FILES"; fi | \
	xargs -n 1500 $(YAPF) --parallel --style ../.style.yapf --verbose --diff | \
	grep '^+++ .*(reformatted)$$' | \
	sed -e 's/^+++ //' -e 's/[[:blank:]]*(reformatted)$$/:1:1: error: file needs formatting/' ; \
	exit $${PIPESTATUS[0]}

test-format-python-docker:
	../scripts/run-in-docker.sh make --quiet test-format-python

test-format-shell:
	docker run --rm -v "$(realpath ..):/sh" -w /sh peterdavehello/shfmt shfmt -d -i 4 -ci $(SHELL_FILES)

test-gui-crawl: prepare-node-modules
	$(PYTEST) -T gui_crawl $(realpath gui_crawl/test_gui_crawl.py)

test-gui-crawl-docker:
	$(PIPENV) run scripts/run-dockerized.py "test-gui-crawl"

test-integration: prepare-node-modules
	CI=true $(PIPENV) run scripts/run-integration-test.py $(realpath integration)

test-integration-docker:
	$(PIPENV) run scripts/run-dockerized.py "test-integration"

test-mypy:
	$(FIND_PYTHON_FILES) | \
	`: filter out plugins, they are not real modules` \
	grep -v $$(realpath '../checks') | \
	grep -v $$(realpath '../inventory') | \
	if test -d ../enterprise; then \
	    grep -v $$(realpath '../agents')/bakery; \
	else \
	    cat; \
	fi | xargs -n 1500 $(MYPY) $(ADDITIONAL_MYPY_ARGS)

test-mypy-raw:
	$(MAKE) test-mypy ADDITIONAL_MYPY_ARGS="--config-file=$(realpath ../mypy-raw.ini)"

test-mypy-docker:
	../scripts/run-in-docker.sh make --quiet test-mypy

test-packaging:
	$(PYTEST) -T packaging packaging

test-pipenv-deps:
	$(PIPENV) check

test-pylint:
	$(PYTEST) -T pylint pylint

test-pylint-docker:
	../scripts/run-in-docker.sh make --quiet test-pylint

test-shellcheck:
	@CMK_DIR="$(realpath ..)" ; \
	ENTERPRISE_DIR="$(realpath ../enterprise)" ; \
	shellcheck \
		$(SHELLCHECK_OUTPUT_ARGS) \
		$$(grep -l '^#!/.*sh' $$CMK_DIR/agents/* $$CMK_DIR/agents/plugins/* $$CMK_DIR/agents/special/* 2>/dev/null) \
		"$$ENTERPRISE_DIR/agents/mk-remote-alert-handler"

test-unit:
	$(PYTEST) \
		-T unit \
		--doctest-modules \
		../cmk/base/plugins \
		../cmk/gui \
		../cmk/special_agents \
		../cmk/utils \
		unit

test-unit-docker:
	../scripts/run-in-docker.sh make --quiet test-unit

test-unit-coverage-html:
	$(PYTEST) \
		-T unit \
		--cov=cmk \
		--cov-report=html \
		--cov-config=.coveragerc_unit \
		--no-cov-on-fail \
		--doctest-modules \
		../cmk/base/plugins \
		../cmk/gui \
		../cmk/special_agents \
		../cmk/utils \
		unit

test-unit-sh:
	./sh_test_runner.sh

test-unit-sh-docker:
	../scripts/run-in-docker.sh make test-unit-sh

%-livestatus-docker:
	../scripts/run-in-docker.sh make RESULTS=$(RESULTS) GERRIT_PATCHSET_REVISION=$(GERRIT_PATCHSET_REVISION) $*-livestatus

%-core-docker:
	../scripts/run-in-docker.sh make RESULTS=$(RESULTS) GERRIT_PATCHSET_REVISION=$(GERRIT_PATCHSET_REVISION) $*-core

test-cppcheck-livestatus:
	cd ../livestatus/src && make CPPCHECK_NEB_RESULT=$(RESULTS)/cppcheck-neb.xml $(CPPCHECK)

test-cppcheck-core:
	cd ../enterprise/core/src && make CPPCHECK_CMC_RESULT=$(RESULTS)/cppcheck-cmc.xml $(CPPCHECK)

test-cppcheck-docker:
	../scripts/run-in-docker.sh make -C .. cppcheck-xml

test-tidy-livestatus:
	cd ../livestatus/src && ../../scripts/run-cxx-linter tidy $(GERRIT_PATCHSET_REVISION) $(REDIRECT) $(RESULTS)/livestatus-tidy.txt

test-tidy-core:
	cd ../enterprise/core/src && ../../../scripts/run-cxx-linter tidy $(GERRIT_PATCHSET_REVISION) $(REDIRECT) $(RESULTS)/core-tidy.txt

test-tidy-docker:
	../scripts/run-in-docker.sh make -C .. tidy

test-iwyu-livestatus:
	cd ../livestatus/src && ../../scripts/run-cxx-linter iwyu $(GERRIT_PATCHSET_REVISION) $(REDIRECT) $(RESULTS)/livestatus-iwyu.txt

test-iwyu-core:
	cd ../enterprise/core/src && ../../../scripts/run-cxx-linter iwyu $(GERRIT_PATCHSET_REVISION) $(REDIRECT) $(RESULTS)/core-iwyu.txt

test-iwyu-docker:
	../scripts/run-in-docker.sh make -C .. iwyu

test-unit-livestatus:
	cd ../livestatus/src && ./.f12 $(REDIRECT) $(RESULTS)/livestatus-neb-cmc.txt

test-unit-core:
	cd ../enterprise/core/src && ./.f12 $(REDIRECT) $(RESULTS)/core-neb-cmc.txt
