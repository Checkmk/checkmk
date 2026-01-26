# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

SHELL := /bin/bash -e
SCRIPTS := $(realpath ../scripts)
FIND_PYTHON_FILES := $(SCRIPTS)/find-python-files
FIND_SHELL_FILES := $(SCRIPTS)/find-shell-files
UVENV := $(SCRIPTS)/run-uvenv
PYTEST := $(UVENV) pytest $(PYTEST_ARGS)
CYCLES := $(UVENV) py_import_cycles
PYTEST_OPTS_UNIT_SKIP_SLOW = -m "not slow"
PYTEST_OPTS_UNIT_SLOW_ONLY = -m "slow"
THREE_TO_TWO := $(UVENV) 3to2
BANDIT := $(UVENV) bandit
SEMGREP := $(realpath semgrep)/run-semgrep
SHELLCHECK := bazel run --ui_event_filters=-info,-stderr //bazel/tools:shellcheck_bin --
SHFMT := $(SCRIPTS)/run-bazel.sh run --ui_event_filters=-info,-stderr //bazel/tools:shfmt_bin --
TAPLO := $(SCRIPTS)/run-bazel.sh run --ui_event_filters=-info,-stderr //bazel/tools:taplo_bin --
FIND_INVALID_TEST_FILES := $(SCRIPTS)/find-invalid-autogen-files
ADDITIONAL_MYPY_ARGS := $(JUNIT_XML)
# Please note: We can currently not include defines.make as it would override
# the EDITIONS environment variable handed over by some jenkins test jobs.
# Looks like we need to cleanup the EDITION handling here.
AGENT_PLUGIN_PYTHON_VERSIONS := $(shell make --no-print-directory --file=../defines.make print-AGENT_PLUGIN_PYTHON_VERSIONS)
MAX_CHARS := 1500000

# A random time zone between UTC-11...UTC+14. Note the recursively expanded
# variable assignment to get a new time zone on every access.
RANDOM_TZ = $(shell printf "UTC%+d\n" $$(( $$RANDOM / 1261 - 11 )) )

SYSTEM_TESTS := \
    test-integration \
    test-integration-redfish \
    test-integration-otel \
    test-composition \
    test-update-cre \
    test-update-cee \
    test-update-cce \
    test-update-cme \
    test-update-cse \
    test-update-cross-edition-cee-to-cce \
    test-update-cross-edition-cee-to-cme \
    test-update-cross-edition-cre-to-cce \
    test-update-cross-edition-cre-to-cee \
    test-schemathesis-openapi \
    test-plugins \
    test-plugins-piggyback \
    test-gui-crawl \
    test-xss-crawl \
    test-gui-e2e \
    test-gui-e2e-non-free \
    test-gui-e2e-cee \
    test-gui-e2e-cce \
    test-gui-e2e-cme \
    test-gui-e2e-cse \
    test-extension-compatibility
PYTEST_SYSTEM_TEST_ARGS := -p "no:cov" --log-cli-level=INFO
DOCKERABLE_TESTS := \
	test-bandit \
	test-code-quality \
	test-cycles \
	test-file-content \
	test-format-bazel \
	test-format-python \
	test-format-shell \
	test-format-toml \
	test-license-headers \
	test-lint-bazel \
	test-lint-groovy \
	test-mypy \
	test-requirements \
	test-ruff \
	test-pylint \
	test-shellcheck \
	test-unit-all \
	test-unit-shell \
	test-unit-testlib \
	test-werks \
	test-semgrep

# HINT: the "layering_violation" checker is not production ready and left out on purpose
PYLINT_CUSTOM_CHECKERS := cmk-module-layer-violation,localization-html-tags-checker,localization-literal-string-checker

# Since the unit tests (that are written for Python 3) are executed with Python
# 2.7, we need to convert them, just like it is done for the agent plugins (see
# agents/plugins/Makefile)
AGENT_PLUGIN_UNIT_TEST_FILES := $(wildcard agent-plugin-unit/test_*.py)
AGENT_PLUGIN_UNIT_TEST_FILES_PY2 := $(subst agent-plugin-unit,agent-plugin-unit/py2,$(AGENT_PLUGIN_UNIT_TEST_FILES))

.PHONY: clean format-shell help prepare-protobuf-files prepare-playwright  bandit.ini \
	$(foreach VERS,$(AGENT_PLUGIN_PYTHON_VERSIONS),test-agent-plugin-unit-py$(VERS)-docker) \
	test-bandit test-code-quality test-code-quality-docker
	test-docker test-docker-docker \
	test-integration-agent-plugin test-integration-agent-plugin-docker \
	test-format-python test-format-python-docker \
	test-format-shell test-format-shell-docker \
	format-toml test-format-toml test-format-toml-docker \
	$(SYSTEM_TESTS) \
	$(foreach TEST,$(SYSTEM_TESTS),$(TEST)-docker) \
	container-debug \
	$(foreach TEST,$(SYSTEM_TESTS),$(TEST)-docker-debug) \
	test-mypy test-mypy-raw itest-mypy-docker test-packaging test-pylint test-pylint-docker test-ruff test-ruff-docker \
	test-unit test-unit-all test-unit-docker \
	test-unit-shell test-unit-shell-docker test-shellcheck test-shellcheck-docker test-cycles test-cycles-docker \
	test-unit-omdlib \
	test-tidy-core test-tidy-docker test-iwyu-core test-iwyu-docker \
	test-unit-neb test-unit-core test-flake8 \
	test-semgrep test-semgrep-docker

clean:
	$(RM) -r .mypy_cache $(AGENT_PLUGIN_UNIT_TEST_FILES_PY2)

help:
	@echo "container-debug                     - Run container for manual test debugging"
	@echo "format-shell                        - Format shell agents"
	@echo "format-toml                         - Format toml files"
	@for i in $(AGENT_PLUGIN_PYTHON_VERSIONS); do \
	    echo "test-agent-plugin-unit-py$${i}-docker - Run Agent plugin tests in container with Python $${i}"; \
	done
	@for i in $(SYSTEM_TESTS); do \
	    echo "$${i}              - Run $${i} locally"; \
	    echo "$${i}-docker       - Run $${i} in container"; \
	done
	@for i in $(DOCKERABLE_TESTS); do \
	    echo "$${i}              - Run $${i} locally"; \
	    echo "$${i}-docker       - Run $${i} in container"; \
	done
	@echo "test-bandit-nosec-markers           - Check if all bandit #nosec markers are annotated properly"
	@echo "test-docker                         - Run docker tests"
	@echo "test-docker-docker                  - Run docker tests in docker"
	@echo "test-integration-agent-plugin       - Run agent plugin integration tests"
	@echo "test-integration-agent-plugin-docker - Run agent plugin integration tests in docker"
	@echo "test-mypy-raw                       - Run mypy with raw edition config"
	@echo "test-packaging                      - Run packaging tests"
	@echo "test-unit                           - Run unit tests"
	@echo "test-unit-cmc                       - Run unit tests for cmc"
	@echo "test-unit-docker                    - Run unit tests in docker"
	@echo "test-unit-neb                       - Run unit tests for neb"
bandit.ini:
	( echo -n -e "[bandit]\ntargets: "; \
	  $(FIND_PYTHON_FILES) | tr '\n' ',' | sed 's/,$$//'; \
	  echo ) > bandit.ini
	( echo exclude: /tests >> bandit.ini )

format-shell:
	cd .. && $(SHFMT) -w -i 4 -ci $$($(FIND_SHELL_FILES))

agent-plugin-unit/py2/test_%.py: agent-plugin-unit/test_%.py
	mkdir -p "$(dir $@)"
	cat "$<" | gawk -v text="# Do not test generated 2.x files\n# fmt: off\n# type: ignore" '!/^#/ && !p {print text; p=1} 1' > "$@"
	$(THREE_TO_TWO) --nofix=str --nofix=next --nobackups --write "$@" >/dev/null

$(foreach VERS,$(filter 2.%,$(AGENT_PLUGIN_PYTHON_VERSIONS)),test-agent-plugin-unit-py$(VERS)-docker): $(AGENT_PLUGIN_UNIT_TEST_FILES_PY2)

$(foreach VERS,$(AGENT_PLUGIN_PYTHON_VERSIONS),test-agent-plugin-unit-py$(VERS)-docker):
	@if [ -z ${DOCKER_REGISTRY_NO_HTTPS} ]; then \
  	   echo "DOCKER_REGISTRY_NO_HTTPS is not set, please export this environment variable during make target call."; \
  	   echo "Hint: export DOCKER_REGISTRY_NO_HTTPS=artifacts.lan.tribe29.com:4000"; \
  	   exit 1; \
  	fi; \
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
	IMAGE_HASH="$$(docker build --build-arg DOCKER_REGISTRY="${DOCKER_REGISTRY_NO_HTTPS}" --build-arg PYTHON_VERSION_MAJ_MIN="$$PYTHON_VERSION" -q "$(realpath agent-plugin-unit)")" && \
	echo "Docker image: $$IMAGE_HASH" && \
	if [ ! -d "$$TEST_PATH/datasets" ]; then mkdir "$$TEST_PATH/datasets"; fi && \
	docker run \
	    --rm \
	    $(DOCKER_ADDOPTS) \
	    -e "PYTEST_ADDOPTS" \
	    -e "CI" \
	    -u $$(id -u):$$(id -g) \
	    -v "$$TEST_PATH:/tests" \
	    -v "$(realpath agent-plugin-unit)/datasets:/tests/datasets" \
	    -v "$(realpath ../agents):/agents" \
	    $$IMAGE_HASH \
	    python$$PYTHON_VERSION -m pytest --ignore=tests/py2/ "/tests"

test-semgrep:
	$(SEMGREP) scan \
	    $(SEMGREP_OUTPUT_ARGS) \
	    --config "$(realpath semgrep/rules)" \
	    --quiet \
	    --oss-only \
	    --use-git-ignore \
	    --exclude=$(realpath ..)/packages \
	    --disable-version-check \
	    --error \
	    $(realpath ..)

test-bandit: bandit.ini
# Currently only care about high severity reported issues. Once this is reached,
# go and enable the medium/low checks.
	$(BANDIT) -c ../bandit.yaml -r -ll --ini bandit.ini $(BANDIT_OUTPUT_ARGS)

test-bandit-nosec-markers:
	$(UVENV) python bandit-nosec-markers/nosec_reason.py --doc bandit-nosec-markers/bandit-exclusions.md check $(realpath ..)

prepare-protobuf-files:
	$(MAKE) -C .. protobuf-files

prepare-playwright:
	$(UVENV) playwright install-deps "chromium";
	$(UVENV) playwright install "chromium";

test-docker-docker:
	DOCKER_RUN_ADDOPTS="-v $$HOME/.docker/config.json:$$HOME/.docker/config.json:ro -v $$HOME/.cmk-credentials:$$HOME/.cmk-credentials:ro --network=host -e BRANCH -e HOME -e WORKSPACE -e VERSION -e EDITION" \
	    ../scripts/run-in-docker.sh make --quiet test-docker

test-docker:
	docker run --rm -i $$(../buildscripts/docker_image_aliases/resolve.py IMAGE_HADOLINT) < ../docker_image/Dockerfile
	$(SHELLCHECK) -x $(SHELLCHECK_OUTPUT_ARGS) ../docker_image/docker-entrypoint.sh
	$(PYTEST) -x $(realpath docker) $(PYTEST_SYSTEM_TEST_ARGS)

test-integration-agent-plugin-docker:
	DOCKER_RUN_ADDOPTS="-v $$HOME/.docker/config.json:$$HOME/.docker/config.json:ro -v $$HOME/.cmk-credentials:$$HOME/.cmk-credentials:ro --network=host -e BRANCH -e HOME -e WORKSPACE -e VERSION -e EDITION" \
	    ../scripts/run-in-docker.sh make --quiet test-integration-agent-plugin

test-integration-agent-plugin:
	$(PYTEST) -x $(realpath agent_plugin_integration) \
	$(PYTEST_SYSTEM_TEST_ARGS) --session-timeout 3600

test-format-python: test-format-python-sort test-format-python-format

test-format-python-sort: ../pyproject.toml
	echo $$($(FIND_PYTHON_FILES)) | xargs $(MAX_CHARS:%=--max-chars=%) $(UVENV) ruff check --select I --diff | tee -a ../ruff_check_and_format.txt;\
	exit $${PIPESTATUS[1]}

test-format-python-format: ../pyproject.toml
	echo $$($(FIND_PYTHON_FILES)) | xargs $(MAX_CHARS:%=--max-chars=%) $(UVENV) ruff format --check --diff | tee -a ../ruff_check_and_format.txt;\
	exit $${PIPESTATUS[1]}

test-format-shell:
	cd .. && $(SHFMT) -d -i 4 -ci $$($(FIND_SHELL_FILES))

format-toml:
	$(TAPLO) format ../pyproject.toml

test-format-toml:
	$(TAPLO) format --check --diff ../pyproject.toml

test-lint-bazel:
	../scripts/run-buildifier --lint=warn --mode=check

test-format-bazel:
	../scripts/run-buildifier --mode=check

test-lint-groovy:
	cd ..; scripts/run-groovy-lint --loglevel warning --failon error $(GROOVYLINT_OUTPUT_ARGS)

test-performance: prepare-playwright
	$(UVENV) "$(realpath performance)/perftest.sh"

test-performance-docker:
	RESULT_PATH=$(realpath ..) $(UVENV) scripts/run-dockerized.py "$(subst -docker,,$@)"

test-gui-crawl: prepare-playwright
	$(PYTEST) $(PYTEST_SYSTEM_TEST_ARGS) $(realpath gui_crawl/test_gui_crawl.py)

test-xss-crawl: prepare-playwright
	XSS_CRAWL=1 $(PYTEST) $(PYTEST_SYSTEM_TEST_ARGS) $(realpath gui_crawl/test_gui_crawl.py) --numprocesses=1

test-gui-e2e test-gui-e2e-cee: prepare-playwright # full e2e test is done for cee
	EDITION=cee $(PYTEST) --screenshot=only-on-failure --output="$$RESULT_PATH/" --tracing=retain-on-failure \
	$(PYTEST_SYSTEM_TEST_ARGS) $(realpath gui_e2e/)  --numprocesses=1

test-gui-e2e-non-free: prepare-playwright # limited e2e test for non-free editions (cee or higher)
	$(PYTEST) --screenshot=only-on-failure --output="$$RESULT_PATH/" --tracing=retain-on-failure \
	$(PYTEST_SYSTEM_TEST_ARGS) $(realpath gui_e2e/cee)  --numprocesses=1

test-gui-e2e-cce:
	EDITION=cce $(MAKE) test-gui-e2e-non-free

test-gui-e2e-cme:
	EDITION=cme $(MAKE) test-gui-e2e-non-free

test-gui-e2e-cse:
	EDITION=cse $(MAKE) test-gui-e2e-non-free

test-integration:
	$(PYTEST) $(PYTEST_SYSTEM_TEST_ARGS) $(realpath integration) \
	--session-timeout 5400

test-integration-redfish:
	$(PYTEST) $(PYTEST_SYSTEM_TEST_ARGS) \
	$(realpath integration_redfish) --session-timeout 1800

test-integration-otel:
	$(PYTEST) $(PYTEST_SYSTEM_TEST_ARGS) \
	$(realpath integration/otel) --session-timeout 1800

test-composition:
	OTEL_RESOURCE_ATTRIBUTES=service.name=pytest \
	    $(PYTEST) --export-traces $(PYTEST_SYSTEM_TEST_ARGS) \
	    $(realpath composition)

test-extension-compatibility:
	$(PYTEST) -vv $(PYTEST_SYSTEM_TEST_ARGS) $(realpath extension_compatibility)

test-update-cre:
	EDITION=cre $(PYTEST) $(realpath update/cre) $(PYTEST_SYSTEM_TEST_ARGS) -m cre \
	--session-timeout 5400

test-update-cee:
	EDITION=cee $(PYTEST) $(realpath update/cee) $(PYTEST_SYSTEM_TEST_ARGS) -m cee \
	--session-timeout 5400

test-update-cce:
	EDITION=cce $(PYTEST) $(realpath update/cee) $(PYTEST_SYSTEM_TEST_ARGS) -m cce \
	--session-timeout 5400

test-update-cme:
	EDITION=cme $(PYTEST) $(realpath update/cee) $(PYTEST_SYSTEM_TEST_ARGS) -m cme \
	--session-timeout 5400

test-update-cse:
	EDITION=cse $(PYTEST) $(realpath update/cee) $(PYTEST_SYSTEM_TEST_ARGS) -m cse --disable-interactive-mode \
	--session-timeout 5400

test-update-cross-edition-cee-to-cce: # from CEE to CCE
	EDITION=cee $(PYTEST) $(realpath update/cee) $(PYTEST_SYSTEM_TEST_ARGS) $(realpath update/cee/test_update.py) -m cee \
	--latest-base-version --target-edition=CCE --disable-interactive-mode --session-timeout 5400

test-update-cross-edition-cee-to-cme: # from CEE to CME
	EDITION=cee $(PYTEST) $(realpath update/cee) $(PYTEST_SYSTEM_TEST_ARGS) $(realpath update/cee/test_update.py) -m cee \
	--latest-base-version --target-edition=CME --disable-interactive-mode --session-timeout 5400

test-update-cross-edition-cre-to-cee: # from CRE to CEE
	EDITION=cre $(PYTEST) $(PYTEST_SYSTEM_TEST_ARGS) $(realpath update/cre/test_update.py) -m cre \
	--latest-base-version --target-edition=CEE --disable-interactive-mode --session-timeout 5400

test-update-cross-edition-cre-to-cce: # from CRE to CCE
	EDITION=cre $(PYTEST) $(PYTEST_SYSTEM_TEST_ARGS) $(realpath update/cre/test_update.py) -m cre \
	--latest-base-version --target-edition=CCE --disable-interactive-mode --session-timeout 5400

test-schemathesis-openapi:
	SCHMATHESIS_PROFILE=ci $(PYTEST) $(realpath schemathesis_openapi) \
	$(PYTEST_SYSTEM_TEST_ARGS) -p schemathesis -k stateless \
	--html="../results/schemathesis_openapi.html" --self-contained-html

test-plugins:
	$(PYTEST) $(PYTEST_SYSTEM_TEST_ARGS) $(realpath plugins_integration) \
	--ignore=plugins_integration/test_plugin_piggyback.py --session-timeout 7200

test-plugins-piggyback:
	$(PYTEST) $(PYTEST_SYSTEM_TEST_ARGS) \
	$(realpath plugins_integration/test_plugin_piggyback.py) --session-timeout 3600

$(foreach TEST,$(SYSTEM_TESTS),$(TEST)-docker):
	$(UVENV) scripts/run-dockerized.py "$(subst -docker,,$@)"

container-debug $(foreach TEST,$(SYSTEM_TESTS),$(TEST)-docker-debug):
	$(UVENV) scripts/run-dockerized.py debug

$(foreach TEST,$(DOCKERABLE_TESTS),$(TEST)-docker):
	../scripts/run-in-docker.sh make --quiet "$(subst -docker,,$@)"

test-license-headers:
	if test -z "$$PYTHON_FILES"; then $(FIND_PYTHON_FILES); else echo "$$PYTHON_FILES"; fi | \
	xargs $(MAX_CHARS:%=--max-chars=%) --no-run-if-empty $(PYTEST) --log-cli-level=INFO $(realpath code_quality/test_license_headers.py) \
	--python-files;

test-requirements:
	$(PYTEST) --log-cli-level=INFO $(realpath code_quality/test_requirements.py);

test-file-content:
	if test -z "$$CHANGED_FILES_REL_FILE"; then \
	    $(PYTEST) --log-cli-level=INFO $(realpath code_quality/file_content) --test-all-files ; \
	else \
	    cat "$$CHANGED_FILES_REL_FILE" | xargs $(MAX_CHARS:%=--max-chars=%) --no-run-if-empty $(PYTEST) --log-cli-level=INFO $(realpath code_quality/file_content) --changed-files ; \
	fi \

test-werks:
	$(PYTEST) --log-cli-level=INFO $(realpath code_quality/test_werks.py);

test-code-quality: test-license-headers test-requirements test-file-content test-werks

test-mypy: prepare-protobuf-files
	cd .. ; $(UVENV) mypy $(MYPY_ADDOPTS) $(ADDITIONAL_MYPY_ARGS) $$($(FIND_PYTHON_FILES))

test-mypy-raw:
	$(MAKE) test-mypy ADDITIONAL_MYPY_ARGS="--config-file=$(realpath ../mypy-raw.ini)"

test-packaging:
	$(PYTEST) --log-cli-level=INFO packaging

test-pylint: prepare-protobuf-files
	cd ..; $(UVENV) pylint --disable=all --enable=$(PYLINT_CUSTOM_CHECKERS) --jobs=6 $(PYLINT_ARGS) $$($(FIND_PYTHON_FILES))
	cd .. && $(PYTEST) \
	    --config-file=pyproject.toml \
	    --override-ini="pythonpath=." \
	    --random-order-bucket=global \
	    --numprocesses=4 \
	    --dist=loadfile \
	    -- \
	    tests/unit/test_pylint_checker_cmk_module_layers.py \
	    tests/unit/test_pylint_checker_localization.py

test-ruff: prepare-protobuf-files
	cd ..; echo $$($(FIND_PYTHON_FILES)) | xargs $(MAX_CHARS:%=--max-chars=%) $(UVENV) ruff check

test-shellcheck:
	cd .. && $(SHELLCHECK) -x $(SHELLCHECK_OUTPUT_ARGS) $$($(FIND_SHELL_FILES))

test-cycles:
	$(CYCLES) \
		--packages \
		    $$($(UVENV) scripts/find_cmk_namespace_package_paths.py) \
		    $$(realpath -L ..)/omd/packages/omd/omdlib \
		--strategy johnson \
		--threshold 12 \
		--verbose

test-unit-omdlib:
	cd .. && TZ=$(RANDOM_TZ) $(PYTEST) \
		--config-file=pyproject.toml \
		--doctest-modules \
		--override-ini="pythonpath=. omd/packages/omd/" \
		$(PYTEST_OPTS_UNIT_SKIP_SLOW) \
		-- \
		omd/packages/omd/ \
		tests/unit/omdlib/

test-doctest:
	mkdir -p ../results; \
	cd .. && \
	    ./scripts/run-bazel.sh test //cmk:doctest | tee results/$@.txt; \
	exit $${PIPESTATUS[0]}

test-unit:
	mkdir -p ../results; \
	cd .. && \
	    ./scripts/run-bazel.sh test --test_verbose_timeout_warnings //tests/unit:all \
	    --test_env=TZ=$(RANDOM_TZ) \
	    --test_arg="-m" --test_arg="not slow" \
	    --test_arg="--numprocesses=4"

test-unit-docker:
	../scripts/run-in-docker.sh '\
	    make --quiet test-unit ;\
	    x=$$? ;\
	    cp -Lr ../bazel-testlogs/tests/ ../results/testlogs ;\
	    exit $$x'

test-unit-all: test-doctest
	cd .. && \
	    ./scripts/run-bazel.sh test --test_verbose_timeout_warnings //tests/unit:all \
	    --test_env=TZ=$(RANDOM_TZ) \
	    --test_arg="--numprocesses=4"

test-unit-testlib:
	find -name '__pycache__' -exec rm -rf {} \; 2> /dev/null || true
	cd .. && TZ=$(RANDOM_TZ) $(PYTEST) \
		--config-file=pyproject.toml \
		--doctest-modules \
		--override-ini="pythonpath=." \
		--override-ini="consider_namespace_packages=true" \
		$(PYTEST_OPTS_UNIT_SKIP_SLOW) \
		-- \
		tests/testlib/

test-agent-plugin:
	make $(foreach VERS,$(AGENT_PLUGIN_PYTHON_VERSIONS),test-agent-plugin-unit-py$(VERS)-docker)

test-agent-plugin-docker:
	../scripts/run-in-docker.sh make test-agent-plugin

test-unit-shell:
	./unit-shell/runner.sh

test-unit-neb:
	cd ../packages/neb/test && ./.f12

test-unit-cmc:
	cd ../non-free/packages/cmc/test && ./.f12

test-find-modified-lock-files:
	scripts/find_modified_lock_files

test-flake8: ../.flake8
	cd ..; $(UVENV) flake8 --jobs=6 $$($(FIND_PYTHON_FILES))

# Run `validate_changes` in live-mode i.e. not creating a JSON file
# containing build steps to be executed by Jenkins but directly running
# them.
what-gerrit-makes:
	WORKSPACE="$$(git rev-parse --show-toplevel)" ; \
	cd "$$WORKSPACE" ; \
	mkdir -p "$$WORKSPACE/results" ; \
	$(UVENV) buildscripts/scripts/validate_changes.py \
	    -e BASE_COMMIT_ID=origin/master \
	    -e WORKSPACE="$$WORKSPACE" \
	    -e RESULTS="$$WORKSPACE/results"
