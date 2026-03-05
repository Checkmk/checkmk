#!/bin/bash
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

oneTimeSetUp() {
    # Source the script under test
    set +euo pipefail
    # shellcheck disable=SC1091
    MK_SOURCE_ONLY="true" source "${UNIT_SH_REPO_PATH}/omd/non-free/relay/install_relay.sh"
    set -euo pipefail
}

setUp() {
    # Source the mocks
    # shellcheck source=tests/unit-shell/relay/mocks.sh
    source "${UNIT_SH_REPO_PATH}/tests/unit-shell/relay/mocks.sh"

    # Create temporary directory for test files
    TEST_DIR=$(mktemp -d)
    export CHECKMK_RELAY_DATA_DIR="${TEST_DIR}/opt/checkmk_relay"
    export CHECKMK_RELAY_BIN_DIR="${TEST_DIR}/usr/local/bin"
    export CHECKMK_RELAY_SYSTEMD_DIR="${TEST_DIR}/etc/systemd/system"
    export CHECKMK_RELAY_QUADLET_DIR="${TEST_DIR}/etc/containers/systemd"

    # System mode requires root — mock as root by default
    # shellcheck disable=SC2317
    get_euid() { echo 0; }
    export -f get_euid
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
        main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "server.example.com" \
            --target-site-name "mysite" \
            --token "testtoken" 2>&1
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
        main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "server.example.com" \
            --target-site-name "mysite" \
            --token "testtoken" 2>&1
    )
    local exit_code=$?
    set -e

    # Assert that main exited with error
    assertNotEquals "main should exit with error" 0 "$exit_code"

    # Assert that the error message contains the expected text
    echo "$output" | grep -q "Podman is not installed."
    assertTrue "Error message should mention podman not installed" $?
}

# Test: script runs as non-root
# System mode requires root; if run as a regular user it should fail
test_runs_as_non_root() {
    # Mock get_euid to return 1000 (non-root)
    # shellcheck disable=SC2317
    get_euid() { echo 1000; }
    export -f get_euid

    # Run main in a subshell to capture output and exit code
    set +e
    output=$(
        set -euo pipefail
        main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "server.example.com" \
            --target-site-name "mysite" \
            --token "testtoken" 2>&1
    )
    local exit_code=$?
    set -e

    # Assert that main exited with error
    assertNotEquals "main should exit with error" 0 "$exit_code"

    # Assert that the error message contains the expected text
    echo "$output" | grep -q "This script must run as root."
    assertTrue "Error message should mention running as root required" $?
}

# shellcheck disable=SC1090
source "$UNIT_SH_SHUNIT2"
