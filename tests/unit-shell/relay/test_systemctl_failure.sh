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

    # Create a file to track systemctl calls
    SYSTEMCTL_CALLS_FILE="${TEST_DIR}/systemctl_calls.log"
    export SYSTEMCTL_CALLS_FILE
    touch "$SYSTEMCTL_CALLS_FILE"
}

tearDown() {
    # Clean up temporary directory
    if [ -n "${TEST_DIR:-}" ] && [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
}

# Test: systemctl daemon-reload fails
# If systemctl daemon-reload fails, main should exit with error and display the error message
test_systemctl_daemon_reload_failure() {
    # Mock systemctl to fail on daemon-reload but track all calls
    # shellcheck disable=SC2317
    systemctl() {
        echo "systemctl $*" >>"$SYSTEMCTL_CALLS_FILE"
        if [[ "$*" == *"daemon-reload"* ]]; then
            return 1 # Simulate daemon-reload failure
        else
            return 0 # Other systemctl commands succeed
        fi
    }
    export -f systemctl

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
    echo "$output" | grep -q "Call to systemctl daemon-reload failed"
    assertTrue "Error message should mention systemctl daemon-reload failed" $?

    # Assert that systemctl daemon-reload was called
    grep -q "systemctl --user daemon-reload" "$SYSTEMCTL_CALLS_FILE"
    assertTrue "systemctl daemon-reload should have been called" $?

    # Assert that subsequent systemctl enable commands were NOT called
    grep -q "systemctl --user enable" "$SYSTEMCTL_CALLS_FILE" && fail="true" || fail="false"
    assertEquals "systemctl enable should not have been called" "false" "$fail"
}

# Test: systemctl enable path unit fails
# If systemctl enable path unit fails, main should exit with error and display the error message
test_systemctl_enable_path_failure() {
    # Mock systemctl to fail on enable path unit but track all calls
    # shellcheck disable=SC2317
    systemctl() {
        echo "systemctl $*" >>"$SYSTEMCTL_CALLS_FILE"
        if [[ "$*" == *"enable"* ]] && [[ "$*" == *"checkmk_relay-update-manager.path"* ]]; then
            return 1 # Simulate enable path unit failure
        else
            return 0 # Other systemctl commands succeed
        fi
    }
    export -f systemctl

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
    echo "$output" | grep -q "Call to systemctl enable path unit failed"
    assertTrue "Error message should mention systemctl enable path unit failed" $?

    # Assert that systemctl daemon-reload was called
    grep -q "systemctl --user daemon-reload" "$SYSTEMCTL_CALLS_FILE"
    assertTrue "systemctl daemon-reload should have been called" $?

    # Assert that systemctl enable path was called
    grep -q "systemctl --user enable --now checkmk_relay-update-manager.path" "$SYSTEMCTL_CALLS_FILE"
    assertTrue "systemctl enable path should have been called" $?

    # Assert that subsequent systemctl enable service command was NOT called
    grep -q "systemctl --user enable --now checkmk_relay-update-manager.service" "$SYSTEMCTL_CALLS_FILE" && fail="true" || fail="false"
    assertEquals "systemctl enable service should not have been called" "false" "$fail"
}

# Test: systemctl enable update service fails.
# If systemctl enable update service fails, main should exit with error and display the error message
test_systemctl_enable_update_service_failure() {
    # Mock systemctl to fail on enable update service but track all calls
    # shellcheck disable=SC2317
    systemctl() {
        echo "systemctl $*" >>"$SYSTEMCTL_CALLS_FILE"
        if [[ "$*" == *"enable"* ]] && [[ "$*" == *"checkmk_relay-update-manager.service"* ]]; then
            return 1 # Simulate enable update service failure
        else
            return 0 # Other systemctl commands succeed
        fi
    }
    export -f systemctl

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
    echo "$output" | grep -q "Call to systemctl enable update service failed"
    assertTrue "Error message should mention systemctl enable update service failed" $?

    # Assert that systemctl daemon-reload was called
    grep -q "systemctl --user daemon-reload" "$SYSTEMCTL_CALLS_FILE"
    assertTrue "systemctl daemon-reload should have been called" $?

    # Assert that systemctl enable path was called
    grep -q "systemctl --user enable --now checkmk_relay-update-manager.path" "$SYSTEMCTL_CALLS_FILE"
    assertTrue "systemctl enable path should have been called" $?

    # Assert that systemctl enable service was called
    grep -q "systemctl --user enable --now checkmk_relay-update-manager.service" "$SYSTEMCTL_CALLS_FILE"
    assertTrue "systemctl enable service should have been called" $?

    # Assert that subsequent systemctl start command was NOT called
    grep -q "systemctl --user start checkmk_relay.service" "$SYSTEMCTL_CALLS_FILE" && fail="true" || fail="false"
    assertEquals "systemctl start relay service should not have been called" "false" "$fail"
}

# Test: systemctl start relay service fails.
# If systemctl start relay service fails, main should exit with error and display the error message
test_systemctl_start_relay_service_failure() {
    # Mock systemctl to fail on start relay service but track all calls
    # shellcheck disable=SC2317
    systemctl() {
        echo "systemctl $*" >>"$SYSTEMCTL_CALLS_FILE"
        if [[ "$*" == *"start"* ]] && [[ "$*" == *"checkmk_relay.service"* ]]; then
            return 1 # Simulate start relay service failure
        else
            return 0 # Other systemctl commands succeed
        fi
    }
    export -f systemctl

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
    echo "$output" | grep -q "Call to systemctl start relay service failed"
    assertTrue "Error message should mention systemctl start relay service failed" $?

    # Assert that systemctl daemon-reload was called
    grep -q "systemctl --user daemon-reload" "$SYSTEMCTL_CALLS_FILE"
    assertTrue "systemctl daemon-reload should have been called" $?

    # Assert that systemctl enable path was called
    grep -q "systemctl --user enable --now checkmk_relay-update-manager.path" "$SYSTEMCTL_CALLS_FILE"
    assertTrue "systemctl enable path should have been called" $?

    # Assert that systemctl enable service was called
    grep -q "systemctl --user enable --now checkmk_relay-update-manager.service" "$SYSTEMCTL_CALLS_FILE"
    assertTrue "systemctl enable service should have been called" $?

    # Assert that systemctl start relay service was called
    grep -q "systemctl --user start checkmk_relay.service" "$SYSTEMCTL_CALLS_FILE"
    assertTrue "systemctl start relay service should have been called" $?
}

# shellcheck disable=SC1090
source "$UNIT_SH_SHUNIT2"
