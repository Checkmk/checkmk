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
}

tearDown() {
    # Clean up temporary directory
    if [ -n "${TEST_DIR:-}" ] && [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
}

# Helper function to setup mocks for testing missing commands
setup_missing_command() {
    local missing_command="$1"
    export MISSING_COMMAND="$missing_command"

    # Mock command to simulate missing specified command
    # shellcheck disable=SC2317
    command() {
        if [[ "$1" == "-v" && "$2" == "$MISSING_COMMAND" ]]; then
            return 1 # specified command not found
        elif [[ "$1" == "-v" ]]; then
            return 0 # other commands are found
        else
            builtin command "$@"
        fi
    }
    export -f command
}

# Test: systemctl command is missing
# If systemctl is not found, main should fail with appropriate error message
test_missing_systemd() {
    setup_missing_command "systemctl"

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

    # Assert that the error message contains the expected text
    echo "$output" | grep -q "Systemd (systemctl) is not found."
    assertTrue "Error message should mention systemctl not found" $?
}

# Test: podman command is missing
# If podman is not found, main should fail with appropriate error message
test_missing_podman() {
    setup_missing_command "podman"

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

    # Assert that the error message contains the expected text
    echo "$output" | grep -q "Podman is not installed."
    assertTrue "Error message should mention podman not installed" $?
}

# Test: script runs as root
# If script is run as root (EUID=0), main should fail with appropriate error message
test_runs_as_root() {
    # Mock get_euid to return 0 (root)
    # shellcheck disable=SC2317
    get_euid() { echo 0; }
    export -f get_euid

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

    # Assert that the error message contains the expected text
    echo "$output" | grep -q "This script must run as a regular user, not root."
    assertTrue "Error message should mention running as root" $?
}

# shellcheck disable=SC1090
source "$UNIT_SH_SHUNIT2"
