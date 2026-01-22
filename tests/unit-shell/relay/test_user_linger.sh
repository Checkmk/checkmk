#!/bin/bash
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

oneTimeSetUp() {
    # Disable strict mode temporarily to avoid issues during setup
    set +euo pipefail
    MK_SOURCE_ONLY="true" source "${UNIT_SH_REPO_PATH}/omd/non-free/relay/install_relay.sh"
    set -euo pipefail
}

setUp() {
    # Create temporary directory for test files
    TEST_DIR=$(mktemp -d)
    export XDG_CONFIG_HOME="${TEST_DIR}/.config"
    export XDG_DATA_HOME="${TEST_DIR}/.local/share"
    export HOME="${TEST_DIR}"
    export USER="testuser"

    # Source the mocks
    # shellcheck source=tests/unit-shell/relay/mocks.sh
    source "${UNIT_SH_REPO_PATH}/tests/unit-shell/relay/mocks.sh"

    # Create a marker file to track if loginctl was called
    LOGINCTL_CALLED_FILE="${TEST_DIR}/loginctl_called"
    export LOGINCTL_CALLED_FILE
}

tearDown() {
    # Clean up temporary directory
    if [ -n "${TEST_DIR:-}" ] && [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
}

# Test: loginctl command fails during main execution
# If loginctl fails during the execution, the whole operation is aborted.
test_main_loginctl_fails() {
    # Mock loginctl function to fail
    # shellcheck disable=SC2317
    loginctl() {
        echo "1" >"$LOGINCTL_CALLED_FILE"
        return 1
    }
    # This makes the function available to child processes/subshells.
    export -f loginctl

    # Run main in a subshell to capture exit
    set +e
    (
        set -euo pipefail

        printf '%s' "testpass" | main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "server.example.com" \
            --target-site-name "mysite" \
            --user "testuser" \
            2>/dev/null
    )
    local exit_code=$?
    set -e

    # Check if loginctl was called
    local loginctl_called=false
    if [ -f "$LOGINCTL_CALLED_FILE" ]; then
        loginctl_called=true
    fi

    assertTrue "loginctl should have been called" "$loginctl_called"
    assertEquals "main should exit with error code" 1 "$exit_code"
}

# shellcheck disable=SC1090
source "$UNIT_SH_SHUNIT2"
