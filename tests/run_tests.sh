#!/usr/bin/env bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_PATH="$(cd "$SCRIPT_DIR/.." && pwd)"
SCRIPTS="$REPO_PATH/scripts"
UVENV="$SCRIPTS/run-uvenv"
EDITION="${EDITION:-pro}"
MAX_CHARS=1500000

AGENT_PLUGIN_PYTHON_VERSIONS=$(grep -oP '^\s*AGENT_PLUGIN_PYTHON_VERSIONS\s*:=\s*\K.*' "${REPO_PATH}"/defines.make)

# Re-evaluate TEST_FILTER as shell tokens so that shell-quoted expressions like
# e.g. '-m "foo and bar"' split into proper arguments matching
eval "_test_filter_args=(${TEST_FILTER:-})"
PYTEST_SYSTEM_TEST_ARGS=(
    "${_test_filter_args[@]}"
    ${FAKED_ARTIFACTS:+"$FAKED_ARTIFACTS"}
    -p "no:cov"
    --log-cli-level=INFO
    --log-cli-format="%(asctime)s.%(msecs)03d %(levelname)s %(message)s"
)

PYTEST_OPTS_UNIT_SKIP_SLOW=(-m "not slow")
PYTEST_OPTS_UNIT_SLOW_ONLY=(-m "slow")

_random_tz() {
    printf "UTC%+d\n" $((RANDOM / 1261 - 11))
}

_pytest() {
    $UVENV pytest ${PYTEST_ARGS:-} "$@"
}

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

help() {
    cat <<'EOF'
Usage: ./run_tests.sh <target> [args...]

AGENT PLUGIN TESTS
  test-agent-plugin-unit-py<VER>-docker  Run agent plugin tests in container with Python <VER>
  test-agent-plugin                       Run all agent plugin docker tests
  test-agent-plugin-docker                Run all agent plugin docker tests via run-in-docker.sh

SYSTEM TESTS (local / -docker variant available for each)
  test-system-singlesite                  Run single site system tests locally
  test-system-singlesite-k8s              Run single site system tests (not requires_non_root_user)
  test-system-singlesite-non-root         Run single site system tests (requires_non_root_user)
  test-system-redfish                     Run system tests for redfish
  test-system-relay                       Run system tests for the relay (ultimate edition)
  test-system-mk-oracle                   Run system tests for the mk_oracle agent plugins
  test-system-otel                        Run system tests for otel (ultimate edition)
  test-system-mcp                         Run system tests for the mcp-server (pro edition)
  test-system-oauth                       Run system tests for the oauth authorization server (pro edition)
  test-system-multisite                   Run multisite system tests
  test-system-update-community            Run update tests for community edition
  test-system-update-pro                  Run update tests for pro edition
  test-system-update-ultimate             Run update tests for ultimate edition
  test-system-update-ultimatemt           Run update tests for ultimatemt edition
  test-system-update-cloud                Run update tests for cloud edition
  test-system-update-cross-edition-pro-to-ultimate
  test-system-update-cross-edition-pro-to-ultimatemt
  test-system-update-cross-edition-community-to-ultimate
  test-system-update-cross-edition-community-to-pro
  test-system-plugins                     Run plugin system tests
  test-system-plugins-piggyback           Run piggyback plugin system tests
  test-system-gui-crawl                   Run GUI crawl tests
  test-system-gui-crawl-xss               Run XSS crawl tests
  test-system-gui                         Run full GUI system tests (pro edition)
  test-system-gui-pro                     Run full GUI system tests (pro edition)
  test-system-gui-non-free                Run limited GUI system tests (non-free editions)
  test-system-gui-ultimate                Run limited GUI system tests (ultimate edition)
  test-system-gui-ultimatemt              Run limited GUI system tests (ultimatemt edition)
  test-system-gui-cloud                   Run limited GUI system tests (cloud edition)
  test-extension-compatibility            Run extension compatibility tests

SITELESS TESTS (local / -docker variant available for each)
  test-format                             Run format checks via bazel
  test-license-headers                    Run license header checks via bazel
  test-mypy                               Run mypy type checks
  test-plugins-siteless                   Run siteless plugin tests
  test-unit-all                           Run all unit tests including doctests
  test-unit-testlib                       Run testlib unit tests

UNIT TESTS
  test-unit                               Run unit tests (not slow, respects EDITION)
  test-unit-docker                        Run unit tests in docker
  test-unit-all                           Run all unit tests including doctests
  test-unit-neb                           Run unit tests for neb
  test-unit-cmc                           Run unit tests for cmc
  test-unit-omdlib                        Run unit tests for omdlib

MYPY / FORMAT / PACKAGING
  test-mypy                               Run mypy (alias for test-mypy-cmk)
  test-mypy-cmk                           Run mypy on cmk targets
  test-mypy-gpl                           Run mypy with GPL config
  test-packaging                          Run packaging tests
  test-github-actions                     Run format, lint, unit tests, and mypy (community edition)

OTHER TESTS
  test-docker                             Run docker tests
  test-docker-docker                      Run docker tests in docker
  test-performance                        Run performance tests
  test-performance-docker                 Run performance tests in docker
  test-performance-all                    Run all Bazel-based performance suites
  test-performance-all-docker             Run all Bazel-based performance suites in docker
  test-doctest                            Run doctests via bazel
  test-unit-shell                         No-op (placeholder)
  test-tidy-core                          (placeholder)
  test-requirements                       Run requirements tests via bazel
  test-py-extensions                      Run Python extension checker via bazel
  test-find-modified-lock-files           Run find_modified_lock_files script
  test-medium-chain                       Run tests marked for the medium test chain
  test-medium-chain-docker                Run medium test chain in docker
  test-medium-chain-list                  List tests marked for the medium test chain

QA METRICS
  qa-metrics-change-quality               Run QA change-quality metric (incremental)
  qa-metrics-change-quality-full          Run QA change-quality metric (full rebuild)
  qa-metrics-change-quality-dryrun        Dry-run QA change-quality metric

UTILITIES
  container-debug                         Run container for manual test debugging
  prepare-playwright                      Install playwright and chromium
  clean                                   Remove .mypy_cache
  what-gerrit-makes                       Run validate_changes.py in live mode
  help                                    Show this help message

ENVIRONMENT VARIABLES
  EDITION           Edition to use (default: pro)
  PYTEST_ARGS       Extra args passed to pytest
  TEST_FILTER       Test filter passed to pytest
  FAKED_ARTIFACTS   Faked artifacts arg passed to pytest
  RESULT_PATH       Path for test result output
  JUNIT_XML         JUnit XML output path
  QA_METRICS_REPO   Repo path for QA metrics (default: REPO_PATH)
  QA_METRICS_BRANCH Branch for QA metrics
  QA_METRICS_FROM   Start date for QA metrics
  QA_METRICS_TO     End date for QA metrics
  QA_METRICS_CHANGE_QUALITY_CSV  CSV output path for QA metrics
  MK_ORACLE_BINARY_PATH  Path for Oracle binary (agent plugin integration)
  DOCKER_REGISTRY_NO_HTTPS  Docker registry without HTTPS (required for agent plugin docker tests)
EOF
}

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

clean() {
    rm -rf "$SCRIPT_DIR/.mypy_cache"
}

prepare-playwright() {
    $UVENV playwright install-deps "chromium"
    $UVENV playwright install "chromium"
}

container-debug() {
    $UVENV "$SCRIPT_DIR/scripts/run-dockerized.py" debug
}

what-gerrit-makes() {
    local workspace
    workspace="$(git -C "$REPO_PATH" rev-parse --show-toplevel)"
    cd "$workspace"
    mkdir -p "$workspace/results"
    $UVENV buildscripts/scripts/validate_changes.py \
        -e BASE_COMMIT_ID=origin/master \
        -e WORKSPACE="$workspace" \
        -e RESULTS="$workspace/results"
}

# ---------------------------------------------------------------------------
# Agent plugin tests
# ---------------------------------------------------------------------------

_test-agent-plugin-unit-py-docker() {
    local python_version="$1"
    if [ -z "${DOCKER_REGISTRY_NO_HTTPS:-}" ]; then
        echo "DOCKER_REGISTRY_NO_HTTPS is not set, please export this environment variable."
        echo "Hint: export DOCKER_REGISTRY_NO_HTTPS=artifacts.lan.tribe29.com:4000"
        exit 1
    fi
    "$SCRIPT_DIR/agent-plugin-unit/bootstrap.sh" --check-sources
    docker run \
        --cpus=2 --memory=2g \
        --rm \
        --workdir /checkmk \
        -v "$REPO_PATH/:/checkmk" \
        -e "PYTEST_ADDOPTS" \
        -e "PYTHON_VERSION_MAJ_MIN=$python_version" \
        -e "PYTHONPATH=/agents/plugins" \
        "${DOCKER_REGISTRY_NO_HTTPS}/python:$python_version" \
        tests/agent-plugin-unit/bootstrap.sh --execute
}

test-agent-plugin() {
    for ver in $AGENT_PLUGIN_PYTHON_VERSIONS; do
        _test-agent-plugin-unit-py-docker "$ver"
    done
}

test-agent-plugin-docker() {
    "$REPO_PATH/scripts/run-in-docker.sh" tests/run_tests.sh test-agent-plugin
}

# ---------------------------------------------------------------------------
# Docker tests
# ---------------------------------------------------------------------------

test-docker() {
    docker run --rm -i "$("$REPO_PATH/buildscripts/docker_image_aliases/resolve.py" IMAGE_HADOLINT)" \
        <"$REPO_PATH/docker_image/Dockerfile"
    _pytest -x "$(realpath "$SCRIPT_DIR/docker")" "${PYTEST_SYSTEM_TEST_ARGS[@]}"
}

test-docker-docker() {
    DOCKER_RUN_ADDOPTS="-v $HOME/.docker/config.json:$HOME/.docker/config.json:ro -v $HOME/.cmk-credentials:$HOME/.cmk-credentials:ro --network=host -e BRANCH -e HOME -e WORKSPACE -e VERSION -e EDITION" \
        "$REPO_PATH/scripts/run-in-docker.sh" tests/run_tests.sh test-docker
}

# ---------------------------------------------------------------------------
# Playwright-based tests
# ---------------------------------------------------------------------------

test-performance() {
    prepare-playwright
    $UVENV "$(realpath "$SCRIPT_DIR/performance/perftest.sh")"
}

test-performance-docker() {
    RESULT_PATH="$(realpath "$SCRIPT_DIR/..")" $UVENV "$SCRIPT_DIR/scripts/run-dockerized.py" "test-performance"
}

test-performance-all() {
    local rc=0
    bazel test --test_output=streamed //tests/performance:bazel_performance || rc=$?
    $UVENV "$(realpath "$SCRIPT_DIR/performance/perftest_upload.sh")" || return "$?"
    return "$rc"
}

test-performance-all-docker() {
    RESULT_PATH="$(realpath "$SCRIPT_DIR/..")" $UVENV "$SCRIPT_DIR/scripts/run-dockerized.py" "test-performance-all"
}

test-system-gui-crawl() {
    prepare-playwright
    _pytest "${PYTEST_SYSTEM_TEST_ARGS[@]}" \
        "$(realpath "$SCRIPT_DIR/system/gui_crawl")/test_gui_crawl.py"
}

test-system-gui-crawl-xss() {
    prepare-playwright
    XSS_CRAWL=1 _pytest "${PYTEST_SYSTEM_TEST_ARGS[@]}" \
        "$(realpath "$SCRIPT_DIR/system/gui_crawl")/test_gui_crawl.py"
}

test-system-gui() {
    prepare-playwright
    _pytest --cmk-edition pro \
        --screenshot=only-on-failure \
        --output="${RESULT_PATH:-/tmp}/" \
        --tracing=retain-on-failure \
        "${PYTEST_SYSTEM_TEST_ARGS[@]}" \
        "$(realpath "$SCRIPT_DIR/system/gui")"
}

test-system-gui-pro() { test-system-gui; }

test-system-gui-non-free() {
    prepare-playwright
    _pytest --screenshot=only-on-failure \
        --output="${RESULT_PATH:-/tmp}/" \
        --tracing=retain-on-failure \
        "${PYTEST_SYSTEM_TEST_ARGS[@]}" \
        --cmk-edition "$EDITION" \
        "$(realpath "$SCRIPT_DIR/system/gui")/nonfree"
}

test-system-gui-ultimate() { EDITION=ultimate test-system-gui-non-free; }
test-system-gui-ultimatemt() { EDITION=ultimatemt test-system-gui-non-free; }
test-system-gui-cloud() { EDITION=cloud test-system-gui-non-free; }

# ---------------------------------------------------------------------------
# System tests
# ---------------------------------------------------------------------------

test-system-singlesite() {
    _pytest "${PYTEST_SYSTEM_TEST_ARGS[@]}" \
        "$(realpath "$SCRIPT_DIR/system/singlesite")" \
        --session-timeout 7200
}

# keep this target in sync with test-system-singlesite-single.groovy
test-system-singlesite-k8s() {
    _pytest "${PYTEST_SYSTEM_TEST_ARGS[@]}" \
        "$(realpath "$SCRIPT_DIR/system/singlesite")" \
        -m "not requires_non_root_user" --session-timeout 7200
}

test-system-singlesite-non-root() {
    _pytest "${PYTEST_SYSTEM_TEST_ARGS[@]}" \
        "$(realpath "$SCRIPT_DIR/system/singlesite")" \
        -m requires_non_root_user --session-timeout 600
}

test-system-redfish() {
    _pytest "${PYTEST_SYSTEM_TEST_ARGS[@]}" \
        "$(realpath "$SCRIPT_DIR/system/redfish")" \
        --session-timeout 1800
}

test-system-relay() {
    _pytest -x "$(realpath "$SCRIPT_DIR/system/relay")" \
        "${PYTEST_SYSTEM_TEST_ARGS[@]}" --session-timeout 3600
}

# Unlike the -docker variants generated further below, which run the site in a
# container via run-dockerized.py, this one only runs the test code itself in a
# build container via run-in-docker.sh. Same for test-system-mk-oracle-docker.
test-system-relay-docker() {
    DOCKER_RUN_ADDOPTS="-v $HOME/.docker/config.json:$HOME/.docker/config.json:ro -v $HOME/.cmk-credentials:$HOME/.cmk-credentials:ro --network=host -e BRANCH -e HOME -e WORKSPACE -e VERSION -e EDITION" \
        "$REPO_PATH/scripts/run-in-docker.sh" tests/run_tests.sh test-system-relay
}

test-system-mk-oracle() {
    _pytest -x "$(realpath "$SCRIPT_DIR/system/mk_oracle")" \
        "${PYTEST_SYSTEM_TEST_ARGS[@]}" --session-timeout 3600 \
        --log-cli-level=INFO -o junit_logging=all \
        ${RESULT_PATH:+--junitxml="$RESULT_PATH/junit.xml"} \
        ${MK_ORACLE_BINARY_PATH:+"$MK_ORACLE_BINARY_PATH"}
}

test-system-mk-oracle-docker() {
    DOCKER_RUN_ADDOPTS="-v $HOME/.docker/config.json:$HOME/.docker/config.json:ro -v $HOME/.cmk-credentials:$HOME/.cmk-credentials:ro --network=host -e BRANCH -e HOME -e WORKSPACE -e VERSION -e EDITION" \
        "$REPO_PATH/scripts/run-in-docker.sh" tests/run_tests.sh test-system-mk-oracle
}

test-system-otel() {
    EDITION=ultimate _pytest "${PYTEST_SYSTEM_TEST_ARGS[@]}" \
        "$(realpath "$SCRIPT_DIR/system/singlesite")/nonfree/ultimate/otel/" \
        --session-timeout 1800
}

test-system-mcp() {
    EDITION=pro _pytest "${PYTEST_SYSTEM_TEST_ARGS[@]}" \
        "$(realpath "$SCRIPT_DIR/system/singlesite")/nonfree/pro/mcp/" \
        --session-timeout 1800
}

test-system-azure-extended-ultimate() {
    EDITION=ultimate _pytest "${PYTEST_SYSTEM_TEST_ARGS[@]}" \
        "$(realpath "$SCRIPT_DIR/system/singlesite")/nonfree/ultimate/azure_extended/" \
        --session-timeout 1800
}

test-system-oauth() {
    EDITION=pro _pytest "${PYTEST_SYSTEM_TEST_ARGS[@]}" \
        "$(realpath "$SCRIPT_DIR/system/singlesite")/cmk/gui/oauth/" \
        --session-timeout 1800
}

test-system-multisite() {
    OTEL_RESOURCE_ATTRIBUTES=service.name=pytest \
        _pytest --export-traces "${PYTEST_SYSTEM_TEST_ARGS[@]}" \
        "$(realpath "$SCRIPT_DIR/system/multisite")"
}

test-extension-compatibility() {
    _pytest -vv "${PYTEST_SYSTEM_TEST_ARGS[@]}" \
        "$(realpath "$SCRIPT_DIR/extension_compatibility")"
}

# ---------------------------------------------------------------------------
# Update tests
# ---------------------------------------------------------------------------

test-system-update-community() {
    _pytest --cmk-edition community \
        "$(realpath "$SCRIPT_DIR/system/update")/community" \
        "${PYTEST_SYSTEM_TEST_ARGS[@]}" --session-timeout 5400
}

test-system-update-pro() {
    _pytest --cmk-edition pro \
        "$(realpath "$SCRIPT_DIR/system/update")/nonfree" \
        "${PYTEST_SYSTEM_TEST_ARGS[@]}" --session-timeout 5400
}

test-system-update-ultimate() {
    _pytest --cmk-edition ultimate \
        "$(realpath "$SCRIPT_DIR/system/update")/nonfree" \
        "${PYTEST_SYSTEM_TEST_ARGS[@]}" --session-timeout 9000
}

test-system-update-ultimatemt() {
    _pytest --cmk-edition ultimatemt \
        "$(realpath "$SCRIPT_DIR/system/update")/nonfree" \
        "${PYTEST_SYSTEM_TEST_ARGS[@]}" --session-timeout 9000
}

test-system-update-cloud() {
    _pytest --cmk-edition cloud \
        "$(realpath "$SCRIPT_DIR/system/update")/nonfree" \
        "${PYTEST_SYSTEM_TEST_ARGS[@]}" \
        --disable-interactive-mode --session-timeout 5400
}

test-system-update-cross-edition-pro-to-ultimate() {
    _pytest --cmk-edition pro \
        "$(realpath "$SCRIPT_DIR/system/update")/nonfree/pro/test_update.py" \
        "${PYTEST_SYSTEM_TEST_ARGS[@]}" \
        --latest-base-version --target-edition=ultimate \
        --disable-interactive-mode --session-timeout 5400
}

test-system-update-cross-edition-pro-to-ultimatemt() {
    _pytest --cmk-edition pro \
        "$(realpath "$SCRIPT_DIR/system/update")/nonfree/pro/test_update.py" \
        "${PYTEST_SYSTEM_TEST_ARGS[@]}" \
        --latest-base-version --target-edition=ultimatemt \
        --disable-interactive-mode --session-timeout 5400
}

test-system-update-cross-edition-community-to-pro() {
    _pytest --cmk-edition community \
        "$(realpath "$SCRIPT_DIR/system/update")/community/test_update.py" \
        "${PYTEST_SYSTEM_TEST_ARGS[@]}" \
        --latest-base-version --target-edition=pro \
        --disable-interactive-mode --session-timeout 5400
}

test-system-update-cross-edition-community-to-ultimate() {
    _pytest --cmk-edition community \
        "$(realpath "$SCRIPT_DIR/system/update")/community/test_update.py" \
        "${PYTEST_SYSTEM_TEST_ARGS[@]}" \
        --latest-base-version --target-edition=ultimate \
        --disable-interactive-mode --session-timeout 5400
}

# ---------------------------------------------------------------------------
# Plugin tests
# ---------------------------------------------------------------------------

test-system-plugins() {
    _pytest "${PYTEST_SYSTEM_TEST_ARGS[@]}" \
        "$(realpath "$SCRIPT_DIR/system/plugins")" \
        --ignore="$(realpath "$SCRIPT_DIR/system/plugins")/nonfree/pro/test_plugin_piggyback.py" \
        --session-timeout 7200
}

test-system-plugins-piggyback() {
    _pytest "${PYTEST_SYSTEM_TEST_ARGS[@]}" \
        "$(realpath "$SCRIPT_DIR/system/plugins")/nonfree/pro/test_plugin_piggyback.py" \
        --session-timeout 3600
}

test-plugins-siteless() {
    _pytest --log-cli-level=INFO \
        "$(realpath "$SCRIPT_DIR/plugins_siteless")" \
        ${RESULT_PATH:+--junitxml="$RESULT_PATH/junit.xml"} \
        --session-timeout 1800
}

# ---------------------------------------------------------------------------
# Docker variants of system/siteless tests
# ---------------------------------------------------------------------------

_system-tests-docker() {
    local target="$1"
    $UVENV "$SCRIPT_DIR/scripts/run-dockerized.py" "$target"
}

_dockerable-test-docker() {
    local target="$1"
    "$REPO_PATH/scripts/run-in-docker.sh" tests/run_tests.sh $target
}

# System test -docker variants
test-system-singlesite-docker() { _system-tests-docker test-system-singlesite; }
test-system-singlesite-k8s-docker() { _system-tests-docker test-system-singlesite-k8s; }
test-system-singlesite-non-root-docker() { _system-tests-docker test-system-singlesite-non-root; }
test-system-redfish-docker() { _system-tests-docker test-system-redfish; }
test-system-otel-docker() { _system-tests-docker test-system-otel; }
test-system-multisite-docker() { _system-tests-docker test-system-multisite; }
test-system-update-community-docker() { _system-tests-docker test-system-update-community; }
test-system-update-pro-docker() { _system-tests-docker test-system-update-pro; }
test-system-update-ultimate-docker() { _system-tests-docker test-system-update-ultimate; }
test-system-update-ultimatemt-docker() { _system-tests-docker test-system-update-ultimatemt; }
test-system-update-cloud-docker() { _system-tests-docker test-system-update-cloud; }
test-system-update-cross-edition-pro-to-ultimate-docker() { _system-tests-docker test-system-update-cross-edition-pro-to-ultimate; }
test-system-update-cross-edition-pro-to-ultimatemt-docker() { _system-tests-docker test-system-update-cross-edition-pro-to-ultimatemt; }
test-system-update-cross-edition-community-to-ultimate-docker() { _system-tests-docker test-system-update-cross-edition-community-to-ultimate; }
test-system-update-cross-edition-community-to-pro-docker() { _system-tests-docker test-system-update-cross-edition-community-to-pro; }
test-system-plugins-docker() { _system-tests-docker test-system-plugins; }
test-system-plugins-piggyback-docker() { _system-tests-docker test-system-plugins-piggyback; }
test-system-gui-crawl-docker() { _system-tests-docker test-system-gui-crawl; }
test-system-gui-crawl-xss-docker() { _system-tests-docker test-system-gui-crawl-xss; }
test-system-gui-docker() { _system-tests-docker test-system-gui; }
test-system-gui-non-free-docker() { _system-tests-docker test-system-gui-non-free; }
test-system-gui-pro-docker() { _system-tests-docker test-system-gui-pro; }
test-system-gui-ultimate-docker() { _system-tests-docker test-system-gui-ultimate; }
test-system-gui-ultimatemt-docker() { _system-tests-docker test-system-gui-ultimatemt; }
test-system-gui-cloud-docker() { _system-tests-docker test-system-gui-cloud; }
test-extension-compatibility-docker() { _system-tests-docker test-extension-compatibility; }

# Debug variants
test-system-singlesite-docker-debug() { $UVENV "$SCRIPT_DIR/scripts/run-dockerized.py" debug; }
test-system-multisite-docker-debug() { $UVENV "$SCRIPT_DIR/scripts/run-dockerized.py" debug; }
container-debug-docker() { $UVENV "$SCRIPT_DIR/scripts/run-dockerized.py" debug; }

# Siteless test -docker variants
test-format-docker() { _dockerable-test-docker test-format; }
test-license-headers-docker() { _dockerable-test-docker test-license-headers; }
test-mypy-docker() { _dockerable-test-docker test-mypy; }
test-plugins-siteless-docker() { _dockerable-test-docker test-plugins-siteless; }
test-unit-all-docker() { _dockerable-test-docker test-unit-all; }
test-unit-testlib-docker() { _dockerable-test-docker test-unit-testlib; }

# ---------------------------------------------------------------------------
# Format / license / packaging
# ---------------------------------------------------------------------------

test-format() {
    bazel run //:format.check
}

test-license-headers() {
    bazel build \
        --aspects=//bazel/tools:aspects.bzl%license_header_checker \
        //... \
        --@aspect_rules_lint//lint:fail_on_violation=True \
        --//:use_faked_artifacts=True \
        --sandbox_debug --keep_going --test_output=errors
}

test-requirements() {
    bazel test --test_tag_filters=requirements //... \
        --//:use_faked_artifacts=true --keep_going --test_output=errors
}

test-py-extensions() {
    bazel build \
        --aspects=//bazel/tools:aspects.bzl%python_extension_checker \
        //... \
        --@aspect_rules_lint//lint:fail_on_violation=True \
        --keep_going
}

test-packaging() {
    export PATH="$PATH:$(bazel run //bazel/tools:bazel_env print-path)"
    _pytest --log-cli-level=INFO "$SCRIPT_DIR/packaging"
}

# ---------------------------------------------------------------------------
# Mypy
# ---------------------------------------------------------------------------

test-mypy() { test-mypy-cmk; }

test-mypy-cmk() {
    bazel build --config=mypy ...
}

test-mypy-not-cmk() {
    : # no-op
}

test-mypy-gpl() {
    ADDITIONAL_MYPY_ARGS="--config-file=$(realpath "$REPO_PATH/mypy-gpl.ini")" \
        bazel build --config=mypy ...
}

test-github-actions() {
    EDITION=community bazel run //:format.check
    EDITION=community bazel lint --fixes=false ...
    EDITION=community "$0" test-unit
    bazel build --config=mypy ...
}

# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

test-doctest() {
    mkdir -p "$REPO_PATH/results"
    bazel test --build_tests_only --test_tag_filters=doctest //... |
        tee "$REPO_PATH/results/test-doctest.txt"
    exit "${PIPESTATUS[0]}"
}

test-unit() {
    bazel test --test_verbose_timeout_warnings //tests/unit/... \
        --test_env="TZ=$(_random_tz)" \
        --test_arg="-m" --test_arg="not slow" \
        --cmk_edition="$EDITION"
}

test-unit-docker() {
    "$REPO_PATH/scripts/run-in-docker.sh" bash -c "
        cd tests && ./run_tests.sh test-unit
        x=\$?
        cp -Lr ../bazel-testlogs/tests/ ../results/testlogs
        exit \$x"
}

test-unit-all() {
    test-doctest
    cd "$REPO_PATH"
    bazel test --test_verbose_timeout_warnings //tests/unit/... \
        --test_env="TZ=$(_random_tz)"
}

test-unit-testlib() {
    find . -name '__pycache__' -exec rm -rf {} \; 2>/dev/null || true
    cd "$REPO_PATH"
    TZ="$(_random_tz)" _pytest \
        --config-file=pyproject.toml \
        --doctest-modules \
        --override-ini="pythonpath=." \
        --override-ini="consider_namespace_packages=true" \
        "${PYTEST_OPTS_UNIT_SKIP_SLOW[@]}" \
        -- \
        tests/testlib/
}

test-unit-omdlib() {
    # placeholder — same pattern as test-unit-shell
    :
}

test-unit-shell() {
    : # no-op
}

test-unit-neb() {
    cd "$REPO_PATH/packages/neb/test" && ./.f12
}

test-unit-cmc() {
    cd "$REPO_PATH/non-free/packages/cmc/test" && ./.f12
}

test-find-modified-lock-files() {
    "$SCRIPT_DIR/scripts/find_modified_lock_files"
}

# ---------------------------------------------------------------------------
# Medium chain tests
# ---------------------------------------------------------------------------

TESTS_MEDIUM_CHAIN_OUTFILE="tests_medium_chain_master.list"
TEST_DIRS_MEDIUM_CHAIN=("$(realpath "$SCRIPT_DIR/system/singlesite")" "$(realpath "$SCRIPT_DIR/system/multisite")")

# keep this target in sync with test-system-singlesite-single.groovy
test-medium-chain() {
    _pytest --log-cli-level=INFO -m medium_test_chain \
        "${TEST_DIRS_MEDIUM_CHAIN[@]}"
}

test-medium-chain-docker() {
    $UVENV "$SCRIPT_DIR/scripts/run-dockerized.py" "test-medium-chain"
}

test-medium-chain-list() {
    _pytest --log-cli-level=INFO -m medium_test_chain \
        --collect-only -q \
        "${TEST_DIRS_MEDIUM_CHAIN[@]}" |
        grep "::" \
            >"$TESTS_MEDIUM_CHAIN_OUTFILE"
    if [ -s "$TESTS_MEDIUM_CHAIN_OUTFILE" ]; then
        echo "Written tests to:"
        wc -l "$TESTS_MEDIUM_CHAIN_OUTFILE"
    else
        echo "No tests found with marker 'medium_test_chain'"
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# QA metrics
# ---------------------------------------------------------------------------

_qa_metrics_args() {
    local args=(--repo "${QA_METRICS_REPO:-$REPO_PATH}")
    [ -n "${QA_METRICS_BRANCH:-}" ] && args+=(--branch "$QA_METRICS_BRANCH")
    [ -n "${QA_METRICS_FROM:-}" ] && args+=(--from "$QA_METRICS_FROM")
    [ -n "${QA_METRICS_TO:-}" ] && args+=(--to "$QA_METRICS_TO")
    printf '%s\n' "${args[@]}"
}

qa-metrics-change-quality-dryrun() {
    mapfile -t args < <(_qa_metrics_args)
    bazel run //tests/qa_metrics/change_quality:push -- \
        "${args[@]}" \
        --dry-run --full --format csv \
        --output "${QA_METRICS_CHANGE_QUALITY_CSV:-$REPO_PATH/qa-metrics-change-quality.csv}"
}

qa-metrics-change-quality() {
    mapfile -t args < <(_qa_metrics_args)
    bazel build //tests/qa_metrics/change_quality:push
    "$REPO_PATH/bazel-bin/tests/qa_metrics/change_quality/push" "${args[@]}"
}

qa-metrics-change-quality-full() {
    mapfile -t args < <(_qa_metrics_args)
    bazel build //tests/qa_metrics/change_quality:push
    "$REPO_PATH/bazel-bin/tests/qa_metrics/change_quality/push" "${args[@]}" --full
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

# Handle test-agent-plugin-unit-py<VER>-docker dynamically
_try-agent-plugin-version() {
    local target="$1"
    local ver
    if [[ "$target" =~ ^test-agent-plugin-unit-py(.+)-docker$ ]]; then
        ver="${BASH_REMATCH[1]}"
        _test-agent-plugin-unit-py-docker "$ver"
        return 0
    fi
    return 1
}

main() {
    local target="${1:-help}"
    shift || true

    if _try-agent-plugin-version "$target"; then
        return 0
    fi

    # Convert hyphens to allow function lookup; bash functions can contain hyphens
    if declare -f "$target" >/dev/null 2>&1; then
        "$target" "$@"
    else
        echo "Unknown target: $target" >&2
        echo "Run './run_tests.sh help' for available targets." >&2
        exit 1
    fi
}

main "$@"
