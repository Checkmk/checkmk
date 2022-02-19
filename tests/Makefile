# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

SHELL := /bin/bash -e
SCRIPTS := ../scripts
FIND_PYTHON_FILES := $(SCRIPTS)/find-python-files
PIPENV := $(SCRIPTS)/run-pipenv
PYTEST := $(PIPENV) run py.test $(PYTEST_ARGS)
YAPF := $(PIPENV) run yapf
BLACK  := $(SCRIPTS)/run-black
THREE_TO_TWO := $(PIPENV) run 3to2
BANDIT := $(PIPENV) run bandit
FIND_INVALID_TEST_FILES := $(SCRIPTS)/find-invalid-autogen-files
ADDITIONAL_MYPY_ARGS := $(JUNIT_XML)
# TODO: Remove version duplication, see buildscripts/infrastructure/build-nodes/scripts/install-gnu-toolchain.sh
GCC_TOOLCHAIN := /opt/gcc-11.2.0

# Since the unit tests (that are written for Python 3) are executed with Python
# 2.6 and 2.7, we need to convert them, just like it is done for the agent
# plugins (see agents/plugins/Makefile)
AGENT_PLUGIN_UNIT_TEST_FILES := $(wildcard agent-plugin-unit/test_*.py)
AGENT_PLUGIN_UNIT_TEST_FILES_PY2 := $(subst agent-plugin-unit,agent-plugin-unit/py2,$(AGENT_PLUGIN_UNIT_TEST_FILES))

SHELL_FILES_REL := $(shell cd ..; grep -rl \
    --exclude-dir="buildscripts" \
    --exclude-dir="core" \
    --exclude-dir="doc" \
    --exclude-dir="livestatus" \
    --exclude-dir="node_modules" \
    --exclude-dir="notifications" \
    --exclude-dir="omd" \
    --exclude-dir="skel" \
    --exclude-dir="tests" \
    --exclude="LIVEPROXYD" \
    --exclude="install-sh" \
    --exclude="code_examples.py" \
    '^\#!/.*sh' [^.]* 2>/dev/null)

# Due to https://github.com/pypa/pypi-support/issues/978, we need to disable Plugin tests for py2.6
# until we have a feasible solution or we drop the support for 2.6 completly.
PYTHON_VERSIONS := 2.7 3.3 3.4 3.5 3.6 3.7 3.8 3.9

.PHONY: clean format-shell help prepare-protobuf-files prepare-playwright  bandit.ini \
	$(foreach VERS,$(PYTHON_VERSIONS),test-agent-plugin-unit-py$(VERS)-docker) \
	test-bandit test-composition test-composition-docker test-composition-docker-debug \
	test-docker test-docker-docker test-format-python test-format-python-docker test-format-shell \
	test-format-js test-format-js-docker test-format-css test-format-css-docker \
	test-gui-crawl test-gui-crawl-docker test-xss-crawl test-xss-crawl-docker test-gui-e2e test-gui-e2e-docker \
	test-integration test-integration-docker test-integration-docker-debug \
	test-mypy test-mypy-raw itest-mypy-docker test-packaging test-pipenv-deps test-pylint test-pylint-docker \
	test-unit test-unit-docker test-unit-resilience test-unit-resilience-docker test-unit-coverage-html \
	test-unit-sh test-unit-sh-docker test-shellcheck \
	test-tidy-livestatus test-tidy-core test-tidy-docker test-iwyu-livestatus test-iwyu-core test-iwyu-docker \
	test-unit-livestatus test-unit-core %-livestatus-docker %-core-docker \
	test-cargo-check test-cargo-check-docker test-cargo-test test-cargo-test-docker \
	test-cargo-fmt test-cargo-fmt-docker test-cargo-clippy test-cargo-clippy-docker

clean:
	$(RM) -r .mypy_cache $(AGENT_PLUGIN_UNIT_TEST_FILES_PY2)

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
	@echo "test-docker-docker                  - Run docker tests in docker"
	@echo "test-format-python                  - Run formatting tests"
	@echo "test-format-python-docker           - Run formatting tests in docker"
	@echo "test-format-shell                   - Run the shell formatting"
	@echo "test-format-js                      - Run the JavaScript formatting"
	@echo "test-format-js-docker               - Run the JavaScript formatting in docker"
	@echo "test-format-css                     - Run the CSS formatting"
	@echo "test-format-css-docker              - Run the CSS formatting in docker"
	@echo "test-gui-crawl                      - Run GUI crawl locally"
	@echo "test-gui-crawl-docker               - Run GUI crawl in container"
	@echo "test-xss-crawl                      - Run XSS crawl locally"
	@echo "test-xss-crawl-docker               - Run XSS crawl in container"
	@echo "test-gui-e2e                        - Run GUI End-to-End locally"
	@echo "test-gui-e2e-docker                 - Run GUI End-to-End in container"
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
	@echo "test-unit-resilience                - Run unit tests multiple times and in random order"
	@echo "test-unit-resilience                - Run unit tests multiple times and in random order in docker"
	@echo "test-unit-coverage-html             - Create HTML coverage report for unit tests"
	@echo "test-unit-sh                        - Run shell unit tests"
	@echo "test-unit-sh-docker                 - Run shell unit tests in docker"
	@echo "test-tidy-livestatus                - Run clang tidy for livestatus"
	@echo "test-tidy-core                      - Run clang tidy for core"
	@echo "test-tidy-docker                    - Run clang tidy for core and livestatus in docker"
	@echo "test-iwyu-livestatus                - Run the iwyu tool for livestatus"
	@echo "test-iwyu-core                      - Run the iwyu tool for the core"
	@echo "test-iwyu-docker                    - Run the iwyu tool for both in docker"
	@echo "test-unit-livestatus                - Run unit tests for livestatus"
	@echo "test-unit-core                      - Run unit tests for core"
	@echo "*-livestatus-docker                 - Run any of the livestatus tests in docker"
	@echo "test-cargo-check                    - Run 'cargo check' for all cargo projects"
	@echo "test-cargo-check-docker             - Run 'cargo check' for all cargo projects in docker"
	@echo "test-cargo-test                     - Run test cases of all cargo projects"
	@echo "test-cargo-test-docker              - Run test cases of all cargo projects in docker"
	@echo "test-cargo-fmt                      - Run rustfmt --check in all cargo projects"
	@echo "test-cargo-fmt-docker               - Run rustfmt --check in all cargo projects in docker"
	@echo "test-cargo-clippy                   - Run clippy in all cargo projects"
	@echo "test-cargo-clippy-docker            - Run clippy in all cargo projects in docker"

bandit.ini:
	( echo -n -e "[bandit]\ntargets: "; \
	  $(FIND_PYTHON_FILES) | tr '\n' ',' | sed 's/,$$//'; \
	  echo ) > bandit.ini

format-shell:
	docker run --rm -v "$(realpath ..):/sh" -w /sh peterdavehello/shfmt shfmt -w -i 4 -ci $(SHELL_FILES_REL)

agent-plugin-unit/py2/test_%.py: agent-plugin-unit/test_%.py
	mkdir -p "$(dir $@)"
	cat "$<" | gawk -v text="# Do not test generated 2.x files\n# yapf: disable\n# type: ignore" '!/^#/ && !p {print text; p=1} 1' > "$@"
	$(THREE_TO_TWO) --nofix=str --nobackups --write "$@" >/dev/null

$(foreach VERS,$(filter 2.%,$(PYTHON_VERSIONS)),test-agent-plugin-unit-py$(VERS)-docker): $(AGENT_PLUGIN_UNIT_TEST_FILES_PY2)

$(foreach VERS,$(PYTHON_VERSIONS),test-agent-plugin-unit-py$(VERS)-docker):
	# Clean up auto-generated files, which do not have a corresponding source file anymore
	flock ./agent-plugin-unit $(FIND_INVALID_TEST_FILES)
	# Recursive Makefiles suck big time...
	flock ../agents/plugins $(MAKE) -C ../agents/plugins
	PYTHON_VERSION="$(patsubst test-agent-plugin-unit-py%-docker,%,$@)" ; \
	case $$PYTHON_VERSION in \
	    2.*) SUFFIX="/py2" ;; \
	    *) SUFFIX="" ;; \
	esac ; \
	TEST_PATH="$(realpath agent-plugin-unit)$$SUFFIX" ; \
	IMAGE_HASH="$$(docker build --build-arg PYTHON_VERSION="$$PYTHON_VERSION" -q "$(realpath agent-plugin-unit)")" && \
	echo "Docker image: $$IMAGE_HASH" && \
	docker run \
	    --rm \
	    $(DOCKER_ADDOPTS) \
	    -e "PYTEST_ADDOPTS" \
	    -u $$(id -u):$$(id -g) \
	    -v "$$TEST_PATH:/tests" \
	    -v "$(realpath agent-plugin-unit)/utils.py:/tests/utils.py" \
	    -v "$(realpath agent-plugin-unit)/datasets:/tests/datasets" \
	    -v "$(realpath ../agents/plugins):/plugins" \
	    $$IMAGE_HASH \
	    python$$PYTHON_VERSION -m pytest --ignore=tests/py2/ "/tests"

test-bandit: bandit.ini
# Currently only care about high severity reported issues. Once this is reached,
# go and enable the medium/low checks.
	$(BANDIT) -c ../bandit.yaml -r -lll --ini bandit.ini $(BANDIT_OUTPUT_ARGS)

prepare-protobuf-files:
	$(MAKE) -C .. protobuf-files

prepare-playwright:
	../scripts/run-pipenv run playwright install-deps chromium
	../scripts/run-pipenv run playwright install chromium

test-integration-docker-debug test-composition-docker-debug:
	$(PIPENV) run scripts/run-dockerized.py debug

test-composition-docker:
	$(PIPENV) run scripts/run-dockerized.py "test-composition"

test-composition:
	$(PYTEST) -p no:cov -T composition $(realpath composition)

test-docker-docker:
	DOCKER_RUN_ADDOPTS="-v $$HOME/.docker/config.json:$$HOME/.docker/config.json -v $$HOME/.cmk-credentials:$$HOME/.cmk-credentials --network=host -e HOME -e WORKSPACE -e VERSION -e EDITION" \
	    ../scripts/run-in-docker.sh make --quiet test-docker

test-docker:
	$(MAKE) -C ../docker test-lint-dockerfile test-lint-entrypoint
	$(PYTEST) -x -T docker --log-cli-level=INFO docker

test-format-python: test-format-python-isort test-format-python-black

test-format-python-yapf: ../.style.yapf
# Explicitly specify --style [FILE] to prevent costly searching in parent directories
# for each file specified via command line
#
# There are some mixed up lines on stdout caused by the --parallel option.
# Nevertheless, we keep that option to get a big performance boost. GitHub issue
# opened for this problem: https://github.com/google/yapf/issues/644.
	@if test -z "$${PYTHON_FILES}" && test ! -z "$${PYTHON_FILES+X}"; then exit 0; fi; \
	if test -z "$$PYTHON_FILES"; then $(FIND_PYTHON_FILES); else echo "$$PYTHON_FILES"; fi | \
	xargs -n 1500 $(YAPF) --parallel --style ../.style.yapf --verbose --diff | \
	grep '^+++ .*(reformatted)$$' | \
	sed -e 's/^+++ //' -e 's/[[:blank:]]*(reformatted)$$/:1:1: error: file needs formatting/' ; \
	exit $${PIPESTATUS[1]}

test-format-python-isort: ../pyproject.toml
	if test -z "$$PYTHON_FILES"; then $(FIND_PYTHON_FILES); else echo "$$PYTHON_FILES"; fi | \
	xargs -n 1500 $(PIPENV) run isort --settings-path ../pyproject.toml --check-only --diff \
	exit $${PIPESTATUS[1]}

test-format-python-black: ../pyproject.toml
	if test -z "$$PYTHON_FILES"; then $(FIND_PYTHON_FILES); else echo "$$PYTHON_FILES"; fi | \
	xargs -n 1500 $(BLACK) --check --diff ;\
	exit $${PIPESTATUS[1]}

test-format-python-docker:
	../scripts/run-in-docker.sh make --quiet test-format-python

test-format-shell:
	docker run --rm -v "$(realpath ..):/sh" -w /sh peterdavehello/shfmt shfmt -d -i 4 -ci $(SHELL_FILES_REL)

test-format-js:
	cd ..; scripts/run-prettier --check --no-color --loglevel warn "{enterprise/web,web}/htdocs/js/**/*.js"

test-type-js:
	cd ..; npm run check-types

test-format-js-docker:
	../scripts/run-in-docker.sh make --quiet test-format-js

test-format-css:
	cd ..; scripts/run-prettier --check --no-color --loglevel warn "web/htdocs/themes/**/*.scss"

test-format-css-docker:
	../scripts/run-in-docker.sh make --quiet test-format-css

test-gui-crawl: prepare-playwright
	$(PYTEST) -T gui_crawl --log-cli-level=INFO $(realpath gui_crawl/test_gui_crawl.py)

test-gui-crawl-docker:
	$(PIPENV) run scripts/run-dockerized.py "test-gui-crawl"

test-xss-crawl: prepare-playwright
	XSS_CRAWL=1 $(PYTEST) -T gui_crawl --log-cli-level=INFO $(realpath gui_crawl/test_gui_crawl.py)

test-xss-crawl-docker:
	$(PIPENV) run scripts/run-dockerized.py "test-xss-crawl"

test-integration:
	CI=true $(PIPENV) run scripts/run-integration-test.py $(realpath integration)

test-gui-e2e: prepare-playwright
	$(PYTEST) -T gui_e2e -x --log-cli-level=INFO $(realpath gui_e2e/)

test-gui-e2e-docker:
	$(PIPENV) run scripts/run-dockerized.py "test-gui-e2e"

test-integration-docker:
	$(PIPENV) run scripts/run-dockerized.py "test-integration"

test-mypy: prepare-protobuf-files
	PYTHON_FILES=$$($(FIND_PYTHON_FILES) | \
	`: filter out plugins, they are not real modules` \
	grep -v $$(realpath '../checks') | \
	grep -v $$(realpath '../inventory') | \
	`: files are only needed for pylint to understand the module hierarchy` \
	grep -v $$(realpath -m '../enterprise/cmk/__init__.py') | \
	grep -v $$(realpath -m '../enterprise/cmk/base/__init__.py') | \
	grep -v $$(realpath -m '../plus/cmk/__init__.py') | \
	grep -v $$(realpath -m '../plus/cmk/base/__init__.py') \
	) ; \
	cd .. ; scripts/run-mypy $(MYPY_ADDOPTS) $(ADDITIONAL_MYPY_ARGS) $$PYTHON_FILES

test-mypy-raw:
	$(MAKE) test-mypy ADDITIONAL_MYPY_ARGS="--config-file=$(realpath ../mypy-raw.ini)"

test-mypy-docker:
	../scripts/run-in-docker.sh make --quiet test-mypy

test-packaging:
	$(PYTEST) -T packaging packaging

test-pipenv-deps:
	$(PIPENV) check

test-pylint: prepare-protobuf-files
	$(PYTEST) -T pylint pylint

test-pylint-docker:
	../scripts/run-in-docker.sh make --quiet test-pylint

test-shellcheck:
	cd .. && shellcheck $(SHELLCHECK_OUTPUT_ARGS) $(SHELL_FILES_REL)

test-unit: prepare-protobuf-files
	$(PYTEST) \
		-T unit \
		--doctest-modules \
		../cmk/base \
		../cmk/fields \
		../cmk/gui \
		../cmk/special_agents \
		../cmk/utils \
		../agent-receiver \
		unit

test-unit-docker:
	../scripts/run-in-docker.sh make --quiet test-unit

test-unit-resilience: prepare-protobuf-files
	$(PYTEST) \
		--count=2 \
		--random-order-bucket=global \
		-T unit \
		--doctest-modules \
		../cmk/base \
		../cmk/fields \
		../cmk/gui \
		../cmk/special_agents \
		../cmk/utils \
		../agent-receiver \
	        -m "not non_resilient" \
		unit

test-unit-resilience-docker:
	../scripts/run-in-docker.sh make test-unit-resilience

test-agent-plugin-docker:
	../scripts/run-in-docker.sh make $(foreach VERS,$(PYTHON_VERSIONS),test-agent-plugin-unit-py$(VERS)-docker)

test-unit-coverage-html: prepare-protobuf-files
	$(PYTEST) \
		-T unit \
		--cov=cmk \
		--cov-report=html \
		--cov-config=.coveragerc_unit \
		--no-cov-on-fail \
		--doctest-modules \
		../cmk/base \
		../cmk/fields \
		../cmk/gui \
		../cmk/special_agents \
		../cmk/utils \
		../agent-receiver \
		unit

test-unit-sh:
	./sh_test_runner.sh

test-unit-sh-docker:
	../scripts/run-in-docker.sh make test-unit-sh

%-livestatus-docker:
	../scripts/run-in-docker.sh make RESULTS=$(RESULTS) GERRIT_PATCHSET_REVISION=$(GERRIT_PATCHSET_REVISION) IWYU_EXTRA_ARGS="--gcc-toolchain=$(GCC_TOOLCHAIN)" CLANG_TIDY_EXTRA_ARGS="-extra-arg-before=--gcc-toolchain=$(GCC_TOOLCHAIN)" $*-livestatus

%-core-docker:
	../scripts/run-in-docker.sh make RESULTS=$(RESULTS) GERRIT_PATCHSET_REVISION=$(GERRIT_PATCHSET_REVISION) IWYU_EXTRA_ARGS="--gcc-toolchain=$(GCC_TOOLCHAIN)" CLANG_TIDY_EXTRA_ARGS="-extra-arg-before=--gcc-toolchain=$(GCC_TOOLCHAIN)" $*-core

test-tidy-livestatus:
	cd ../livestatus/src && ../../scripts/run-cxx-linter tidy $(GERRIT_PATCHSET_REVISION)

test-tidy-core:
	cd ../enterprise/core/src && ../../../scripts/run-cxx-linter tidy $(GERRIT_PATCHSET_REVISION)

test-tidy-docker:
	../scripts/run-in-docker.sh make -C .. tidy CLANG_TIDY_EXTRA_ARGS="-extra-arg-before=--gcc-toolchain=$(GCC_TOOLCHAIN)"

test-iwyu-livestatus:
	cd ../livestatus/src && ../../scripts/run-cxx-linter iwyu $(GERRIT_PATCHSET_REVISION)

test-iwyu-core:
	cd ../enterprise/core/src && ../../../scripts/run-cxx-linter iwyu $(GERRIT_PATCHSET_REVISION)

test-iwyu-docker:
	../scripts/run-in-docker.sh make -C .. iwyu IWYU_EXTRA_ARGS="--gcc-toolchain=$(GCC_TOOLCHAIN)"

test-unit-livestatus:
	cd ../livestatus/src && ./.f12

test-unit-core:
	cd ../enterprise/core/src && ./.f12

test-cargo-check:
	$(SCRIPTS)/run-cargo-command-in-projects check --all-targets

test-cargo-check-docker:
	$(SCRIPTS)/run-in-docker.sh make test-cargo-check

test-cargo-test:
	$(SCRIPTS)/run-cargo-command-in-projects test --all-targets

test-cargo-test-docker:
	$(SCRIPTS)/run-in-docker.sh make test-cargo-test

test-cargo-fmt:
	$(SCRIPTS)/run-cargo-command-in-projects fmt -- --check

test-cargo-fmt-docker:
	$(SCRIPTS)/run-in-docker.sh make test-cargo-fmt

test-cargo-clippy:
	$(SCRIPTS)/run-cargo-command-in-projects clippy --all-targets -- -D warnings

test-cargo-clippy-docker:
	$(SCRIPTS)/run-in-docker.sh make test-cargo-clippy

# Run `validate_changes` in live-mode i.e. not creating a JSON file
# containing build steps to be executed by Jenkins but directly running
# them.
what-gerrit-makes:
	WORKSPACE="$$(git rev-parse --show-toplevel)" ; \
	cd "$$WORKSPACE" ; \
	mkdir -p "$$WORKSPACE/results" ; \
	scripts/run-pipenv run buildscripts/scripts/validate_changes.py \
	    -e BASE_COMMIT_ID=origin/master \
	    -e WORKSPACE="$$WORKSPACE" \
	    -e RESULTS="$$WORKSPACE/results"
