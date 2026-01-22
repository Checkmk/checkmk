#!/bin/bash
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

oneTimeSetUp() {
    # Source the script under test
    set +euo pipefail
    MK_SOURCE_ONLY="true" source "${UNIT_SH_REPO_PATH}/omd/non-free/relay/install_relay.sh"
    set -euo pipefail
}

setUp() {
    # Source the mocks
    # shellcheck source=tests/unit-shell/relay/mocks.sh
    source "${UNIT_SH_REPO_PATH}/tests/unit-shell/relay/mocks.sh"

    # Create temporary directory for test files
    TEST_DIR=$(mktemp -d)
    export XDG_CONFIG_HOME="${TEST_DIR}/.config"
    export XDG_DATA_HOME="${TEST_DIR}/.local/share"
    export HOME="${TEST_DIR}"
    export USER="testuser"

    # Create a file to track podman calls
    PODMAN_CALLS_FILE="${TEST_DIR}/podman_calls.log"
    export PODMAN_CALLS_FILE
    touch "$PODMAN_CALLS_FILE"
}

tearDown() {
    # Clean up temporary directory
    if [ -n "${TEST_DIR:-}" ] && [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
}

# Test: Registry is not accessible (podman pull fails)
# If podman pull fails, main should exit with error and podman tag should not be called
test_registry_not_accessible() {
    # Mock podman to fail on pull but track all calls
    # shellcheck disable=SC2317
    podman() {
        echo "podman $*" >>"$PODMAN_CALLS_FILE"
        if [[ "$1" == "pull" ]]; then
            return 1 # Simulate pull failure
        else
            return 0 # Other podman commands succeed
        fi
    }
    export -f podman

    # Run main in a subshell to capture output and exit code
    set +e
    output=$(
        set -euo pipefail
        printf '%s' "testpass" | main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "server.example.com" \
            --target-site-name "mysite" \
            --user "testuser" 2>&1
    )
    local exit_code=$?
    set -e

    # Assert that main exited with error
    assertNotEquals "main should exit with error" 0 "$exit_code"

    # Assert that the error message contains the expected text with full image name
    echo "$output" | grep -q "Pulling relay image docker.io/checkmk/check-mk-relay:1.0.0 failed"
    assertTrue "Error message should mention pulling image failed with full image name" $?

    # Assert that podman pull was called
    grep -q "^podman pull" "$PODMAN_CALLS_FILE"
    assertTrue "podman pull should have been called" $?

    # Assert that podman tag was NOT called
    grep -q "^podman tag" "$PODMAN_CALLS_FILE" && fail="true" || fail="false"
    assertEquals "podman tag should not have been called" "false" "$fail"
}

# shellcheck disable=SC1090
source "$UNIT_SH_SHUNIT2"
