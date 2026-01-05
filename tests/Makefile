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
SHELLCHECK := bazel run --ui_event_filters=-info,-stderr //bazel/tools:shellcheck_bin --
SHFMT := bazel run --ui_event_filters=-info,-stderr //bazel/tools:shfmt --
TAPLO := bazel run --ui_event_filters=-info,-stderr //bazel/tools:taplo_bin --
ADDITIONAL_MYPY_ARGS := $(JUNIT_XML)
# Please note: We can currently not include defines.make as it would override
# the EDITIONS environment variable handed over by some jenkins test jobs.
# Looks like we need to cleanup the EDITION handling here.
AGENT_PLUGIN_PYTHON_VERSIONS := $(shell make --no-print-directory --file=../defines.make print-AGENT_PLUGIN_PYTHON_VERSIONS)
REPO_PATH := $(shell make --no-print-directory --file=../defines.make print-REPO_PATH)
MAX_CHARS := 1500000
EDITION ?= pro

# A random time zone between UTC-11...UTC+14. Note the recursively expanded
# variable assignment to get a new time zone on every access.
RANDOM_TZ = $(shell printf "UTC%+d\n" $$(( $$RANDOM / 1261 - 11 )) )

SYSTEM_TESTS := \
    test-integration \
    test-integration-redfish \
    test-integration-otel \
    test-composition \
    test-update-community \
    test-update-pro \
    test-update-ultimate \
    test-update-ultimatemt \
    test-update-cloud \
    test-update-cross-edition-pro-to-ultimate \
    test-update-cross-edition-pro-to-ultimatemt \
    test-update-cross-edition-community-to-ultimate \
    test-update-cross-edition-community-to-pro \
    test-schemathesis-openapi \
    test-plugins \
    test-plugins-piggyback \
    test-gui-crawl \
    test-xss-crawl \
    test-gui-e2e \
    test-gui-e2e-non-free \
    test-gui-e2e-pro \
    test-gui-e2e-ultimate \
    test-gui-e2e-ultimatemt \
    test-gui-e2e-cloud \
    test-extension-compatibility
PYTEST_SYSTEM_TEST_ARGS := \
    -p "no:cov" \
    --log-cli-level=INFO \
    --log-cli-format="%(asctime)s.%(msecs)03d %(levelname)s %(message)s"
DOCKERABLE_TESTS := \
	test-bandit \
	test-code-quality \
	test-cycles \
	test-file-content \
	test-format \
	test-license-headers \
	test-lint-bazel \
	test-lint-groovy \
	test-mypy \
	test-requirements \
	test-plugins-siteless \
	test-shellcheck \
	test-unit-all \
	test-unit-shell \
	test-unit-testlib \
	test-werks \
	test-semgrep \
	test-medium-chain

# Since the unit tests (that are written for Python 3) are executed with Python
# 2.7, we need to convert them, just like it is done for the agent plugins (see
# agents/plugins/Makefile)
AGENT_PLUGIN_UNIT_TEST_FILES := $(wildcard agent-plugin-unit/test_*.py)

.PHONY: clean help prepare-playwright  \
	$(foreach VERS,$(AGENT_PLUGIN_PYTHON_VERSIONS_DOCKER),test-agent-plugin-unit-py$(VERS)-docker) \
	test-bandit test-code-quality test-code-quality-docker
	test-docker test-docker-docker \
	test-integration-agent-plugin test-integration-agent-plugin-docker \
	test-format \
	$(SYSTEM_TESTS) \
	$(foreach TEST,$(SYSTEM_TESTS),$(TEST)-docker) \
	container-debug \
	$(foreach TEST,$(SYSTEM_TESTS),$(TEST)-docker-debug) \
	test-mypy test-mypy-gpl test-mypy-docker test-packaging \
	test-unit test-unit-all test-unit-docker \
	test-unit-shell test-unit-shell-docker test-shellcheck test-shellcheck-docker test-cycles test-cycles-docker \
	test-unit-omdlib \
	test-tidy-core test-tidy-docker test-iwyu-core test-iwyu-docker \
	test-unit-neb test-unit-core \
	test-semgrep

clean:
	$(RM) -r .mypy_cache

help:
	@echo "container-debug                     - Run container for manual test debugging"
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
	@echo "test-docker                         - Run docker tests"
	@echo "test-docker-docker                  - Run docker tests in docker"
	@echo "test-integration-agent-plugin       - Run agent plugin integration tests"
	@echo "test-integration-agent-plugin-docker - Run agent plugin integration tests in docker"
	@echo "test-mypy-community                 - Run mypy with community config"
	@echo "test-packaging                      - Run packaging tests"
	@echo "test-unit                           - Run unit tests"
	@echo "test-unit-cmc                       - Run unit tests for cmc"
	@echo "test-unit-docker                    - Run unit tests in docker"
	@echo "test-unit-neb                       - Run unit tests for neb"

$(foreach VERS,$(AGENT_PLUGIN_PYTHON_VERSIONS),test-agent-plugin-unit-py$(VERS)-docker):
	@if [ -z ${DOCKER_REGISTRY_NO_HTTPS} ]; then \
	   echo "DOCKER_REGISTRY_NO_HTTPS is not set, please export this environment variable during make target call."; \
	   echo "Hint: export DOCKER_REGISTRY_NO_HTTPS=artifacts.lan.tribe29.com:4000"; \
	   exit 1; \
	fi
	PYTHON_VERSION="$(patsubst test-agent-plugin-unit-py%-docker,%,$@)" ; \
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
	    python$$PYTHON_VERSION -m pytest "/tests"

.PHONY: test-ruff
test-ruff:
	@echo "This target is deprecated, use 'bazel lint [TARGET]' instead."

.PHONY: test-astrein
test-astrein:
	@echo "This target is deprecated, use 'bazel lint [TARGET]' instead."

test-semgrep:
	@echo "This target is deprecated, use 'bazel lint [TARGET]' instead."

test-bandit:
	@echo "This target is deprecated, use 'bazel lint [TARGET]' instead."

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

test-lint-bazel:
	../scripts/run-buildifier --lint=warn --mode=check

test-lint-groovy:
	bazel run //bazel/tools:groovy-lint -- --failon=error --noserver $(GROOVYLINT_OUTPUT_ARGS) $(REPO_PATH)/buildscripts/

test-performance:
	$(UVENV) "$(realpath performance)/perftest.sh"

test-performance-docker:
	RESULT_PATH=$(realpath ..) $(UVENV) scripts/run-dockerized.py "$(subst -docker,,$@)"

test-gui-crawl: prepare-playwright
	$(PYTEST) $(PYTEST_SYSTEM_TEST_ARGS) $(realpath gui_crawl)/test_gui_crawl.py

test-xss-crawl: prepare-playwright
	XSS_CRAWL=1 $(PYTEST) $(PYTEST_SYSTEM_TEST_ARGS) $(realpath gui_crawl)/test_gui_crawl.py --numprocesses=1

test-gui-e2e test-gui-e2e-pro: prepare-playwright # full e2e test is done for pro
	$(PYTEST) --cmk-edition pro --screenshot=only-on-failure --output="$$RESULT_PATH/" --tracing=retain-on-failure \
	$(PYTEST_SYSTEM_TEST_ARGS) $(realpath gui_e2e) --numprocesses=1

test-gui-e2e-non-free: prepare-playwright # limited e2e test for non-free editions (pro or higher)
	$(PYTEST) --screenshot=only-on-failure --output="$$RESULT_PATH/" --tracing=retain-on-failure \
	$(PYTEST_SYSTEM_TEST_ARGS) --cmk-edition $(EDITION) $(realpath gui_e2e)/nonfree --numprocesses=1

test-gui-e2e-ultimate:
	EDITION=ultimate $(MAKE) test-gui-e2e-non-free

test-gui-e2e-ultimatemt:
	EDITION=ultimatemt $(MAKE) test-gui-e2e-non-free

test-gui-e2e-cloud:
	EDITION=cloud $(MAKE) test-gui-e2e-non-free

test-integration:
	$(PYTEST) $(PYTEST_SYSTEM_TEST_ARGS) $(realpath integration) \
	--session-timeout 5400

test-integration-redfish:
	$(PYTEST) $(PYTEST_SYSTEM_TEST_ARGS) \
	$(realpath integration_redfish) --session-timeout 1800

test-integration-otel:
	$(PYTEST) $(PYTEST_SYSTEM_TEST_ARGS) \
	$(realpath integration)/nonfree/ultimate/otel --session-timeout 1800

test-composition:
	OTEL_RESOURCE_ATTRIBUTES=service.name=pytest \
	    $(PYTEST) --export-traces $(PYTEST_SYSTEM_TEST_ARGS) \
	    $(realpath composition)

test-extension-compatibility:
	$(PYTEST) -vv $(PYTEST_SYSTEM_TEST_ARGS) $(realpath extension_compatibility)

test-update-community:
	$(PYTEST) --cmk-edition community $(realpath update)/community $(PYTEST_SYSTEM_TEST_ARGS) --session-timeout 5400

test-update-pro:
	$(PYTEST) --cmk-edition pro $(realpath update)/nonfree/pro $(PYTEST_SYSTEM_TEST_ARGS) --session-timeout 5400

test-update-ultimate:
	$(PYTEST) --cmk-edition ultimate $(realpath update)/nonfree/pro $(PYTEST_SYSTEM_TEST_ARGS) --session-timeout 5400

test-update-ultimatemt:
	$(PYTEST) --cmk-edition ultimatemt $(realpath update)/nonfree/pro $(PYTEST_SYSTEM_TEST_ARGS) --session-timeout 5400

test-update-cloud:
	$(PYTEST) --cmk-edition cloud $(realpath update)/nonfree/pro $(PYTEST_SYSTEM_TEST_ARGS) --disable-interactive-mode \
	--session-timeout 5400

test-update-cross-edition-pro-to-ultimate: # from pro to ultimate
	$(PYTEST) --cmk-edition pro $(realpath update)/nonfree/pro $(PYTEST_SYSTEM_TEST_ARGS) $(realpath update)/nonfree/pro/test_update.py \
	--latest-base-version --target-edition=ultimate --disable-interactive-mode --session-timeout 5400

test-update-cross-edition-pro-to-ultimatemt: # from pro to ultimatemt
	$(PYTEST) --cmk-edition pro $(realpath update)/nonfree/pro $(PYTEST_SYSTEM_TEST_ARGS) $(realpath update)/nonfree/pro/test_update.py \
	--latest-base-version --target-edition=ultimatemt --disable-interactive-mode --session-timeout 5400

test-update-cross-edition-community-to-pro: # from community to pro
	$(PYTEST) --cmk-edition community $(realpath update)/community/test_update.py $(PYTEST_SYSTEM_TEST_ARGS) \
	--latest-base-version --target-edition=pro --disable-interactive-mode --session-timeout 5400

test-update-cross-edition-community-to-ultimate: # from community to ultimate
	$(PYTEST) --cmk-edition community $(realpath update)/community/test_update.py $(PYTEST_SYSTEM_TEST_ARGS) \
	--latest-base-version --target-edition=ultimate --disable-interactive-mode --session-timeout 5400

test-schemathesis-openapi:
	SCHMATHESIS_PROFILE=ci $(PYTEST) $(realpath schemathesis_openapi) \
	$(PYTEST_SYSTEM_TEST_ARGS) -p schemathesis -k stateless \
	--html="../results/schemathesis_openapi.html" --self-contained-html

test-plugins:
	$(PYTEST) $(PYTEST_SYSTEM_TEST_ARGS) $(realpath plugins_integration) \
	--ignore=plugins_integration/nonfree/pro/test_plugin_piggyback.py --session-timeout 7200

test-plugins-piggyback:
	$(PYTEST) $(PYTEST_SYSTEM_TEST_ARGS) \
	$(realpath plugins_integration)/nonfree/pro/test_plugin_piggyback.py --session-timeout 3600

test-plugins-siteless:
	$(PYTEST) --log-cli-level=INFO $(realpath plugins_siteless) \
	--session-timeout 1800

test-plugins-consistency:
	$(PYTEST) --log-cli-level=INFO $(realpath plugins_siteless/plugins_consistency) \
	--session-timeout 1800 --html="../results/plugins-consistency.html" --self-contained-html

$(foreach TEST,$(SYSTEM_TESTS),$(TEST)-docker):
	$(UVENV) scripts/run-dockerized.py "$(subst -docker,,$@)"

container-debug $(foreach TEST,$(SYSTEM_TESTS),$(TEST)-docker-debug):
	$(UVENV) scripts/run-dockerized.py debug

$(foreach TEST,$(DOCKERABLE_TESTS),$(TEST)-docker):
	../scripts/run-in-docker.sh make --quiet "$(subst -docker,,$@)"

test-license-headers:
	if test -z "$$PYTHON_FILES"; then $(FIND_PYTHON_FILES); else echo "$$PYTHON_FILES"; fi | \
	xargs $(MAX_CHARS:%=--max-chars=%) --no-run-if-empty $(PYTEST) --log-cli-level=INFO $(realpath code_quality)/test_license_headers.py \
	--python-files;

test-requirements:
	$(PYTEST) --log-cli-level=INFO $(realpath code_quality)/test_requirements.py;

test-py-extensions:
	# block 1: no changes file given, test all files
	# block 2: changes file given, test only changed files
	if test -z "$$CHANGED_FILES_WITH_MODE_FILE"; then \
		$(PYTEST) --log-cli-level=INFO $(realpath code_quality)/test_python_extensions.py --test-all-files -k 'py_extension' --result-out="$$RESULTS_FILE"; \
	else \
		$(PYTEST) --log-cli-level=INFO $(realpath code_quality)/test_python_extensions.py --git-changes="$$CHANGED_FILES_WITH_MODE_FILE" -k 'py_extension' --result-out="$$RESULTS_FILE"; \
	fi

test-file-content:
	if test -z "$$CHANGED_FILES_REL_FILE"; then \
	    $(PYTEST) --log-cli-level=INFO $(realpath code_quality)/file_content --test-all-files ; \
	else \
	    cat "$$CHANGED_FILES_REL_FILE" | xargs $(MAX_CHARS:%=--max-chars=%) --no-run-if-empty $(PYTEST) --log-cli-level=INFO $(realpath code_quality)/file_content --changed-files ; \
	fi \

test-format:
	bazel run //:format.check

test-werks:
	$(PYTEST) --log-cli-level=INFO $(realpath code_quality)/test_werks.py;

test-code-quality: test-license-headers test-requirements test-file-content test-werks

test-mypy: test-mypy-cmk test-mypy-not-cmk

test-mypy-cmk:
	bazel build --config=mypy //cmk:lib_cmk_repo

test-mypy-not-cmk:
	cd .. && $(UVENV) mypy \
	    $(MYPY_ADDOPTS) \
	    $(ADDITIONAL_MYPY_ARGS) \
	    --config-file="$(REPO_PATH)/pyproject.toml" \
	    -- $$($(FIND_PYTHON_FILES) | grep -v "$(realpath ..)\/cmk\/")

test-mypy-gpl:
	$(MAKE) test-mypy ADDITIONAL_MYPY_ARGS="--config-file=$(realpath ../mypy-gpl.ini)"

test-packaging:
	export PATH=$$PATH:$$(bazel run //bazel/tools:bazel_env print-path); \
	$(PYTEST) --log-cli-level=INFO packaging

test-shellcheck:
	cd .. && $(SHELLCHECK) -x $(SHELLCHECK_OUTPUT_ARGS) $$($(FIND_SHELL_FILES))

test-cycles:
	$(CYCLES) \
		--packages \
		    $$($(UVENV) scripts/find_cmk_namespace_package_paths.py) \
		    $$(realpath -L ..)/omd/packages/omd/omdlib \
		--strategy johnson \
		--threshold 0 \
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
	bazel test //cmk:doctest | tee ../results/$@.txt; \
	exit $${PIPESTATUS[0]}

test-unit:
	bazel test --test_verbose_timeout_warnings //tests/unit:all \
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
	    bazel test --test_verbose_timeout_warnings //tests/unit:all \
	    --test_env=TZ=$(RANDOM_TZ) \
	    --test_arg="--numprocesses=4"

# Default bazel coverage options are defined in .bazelrc.
# With BAZEL_COVERAGE_ARGS you can pass additional arguments to bazel coverage command, for example
# to specify source module to be included in the coverage report with instrumentation_filter option.
# Example:
#    BAZEL_COVERAGE_ARGS='--instrumentation_filter="//(cmk|packages|agents)[/:@]"' make -C tests test-unit-all-coverage
#
test-unit-all-coverage:
	cd .. && \
	    bazel coverage --test_verbose_timeout_warnings //tests/unit:all \
	    --test_env=TZ=$(RANDOM_TZ) \
	    --test_arg="--numprocesses=4" \
	    --test_arg="-m" --test_arg="not skip_on_code_coverage" \
		$(BAZEL_COVERAGE_ARGS) ; \
	    export PATH=$$PATH:$$(bazel run //bazel/tools:bazel_env print-path) && \
		genhtml --title "Checkmk Unit Test Coverage"  \
			--quiet \
			--output results/coverage bazel-out/_coverage/_coverage_report.dat

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

EXCLUDE_PATTERN_MEDIUM_CHAIN := unit|unit-shell|agent-plugin-unit|schemathesis_openapi|qa-test-data
TEST_DIRS_MEDIUM_CHAIN := $(shell find $(realpath) -mindepth 1 -maxdepth 1 -type d | grep -v -E "/($(EXCLUDE_PATTERN_MEDIUM_CHAIN))$$")

test-medium-chain:
	$(PYTEST) --log-cli-level=INFO -m medium_test_chain \
	$(TEST_DIRS_MEDIUM_CHAIN) \
