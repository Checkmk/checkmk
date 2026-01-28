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

# Test: Registration fails (podman run fails)
# If podman run fails during registration, main should exit with error
test_registration_fails() {
    # Mock podman to fail on 'run' with register arguments but track all calls
    # shellcheck disable=SC2317
    podman() {
        echo "podman $*" >>"$PODMAN_CALLS_FILE"
        if [[ "$1" == "run" ]] && [[ "$*" == *"cmk-relay register"* ]]; then
            return 1 # Simulate registration failure
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
            --user "testuser" \
            2>&1
    )
    local exit_code=$?
    set -e

    # Assert that main exited with error
    assertNotEquals "main should exit with error" 0 "$exit_code"

    # Assert that the error message contains the expected text
    echo "$output" | grep -q "Registration failed"
    assertTrue "Error message should mention registration failed" $?

    # Assert that podman run with registration was called
    grep -q "^podman run.*cmk-relay register" "$PODMAN_CALLS_FILE"
    assertTrue "podman run with cmk-relay register should have been called" $?

    # Verify the arguments to podman run for registration
    grep -q "podman run --rm -v relay:/opt/check-mk-relay/workdir localhost/checkmk_relay:checkmk_sync cmk-relay register --server server.example.com --site mysite --relay-alias test-relay --trust-cert --force --user testuser --password testpass" "$PODMAN_CALLS_FILE"
    assertTrue "podman run should have been called with correct registration arguments" $?
}

# Test: Registration with localhost uses host.containers.internal
test_registration_localhost_uses_host_containers_internal() {
    # Mock podman to succeed and track all calls
    # shellcheck disable=SC2317
    podman() {
        echo "podman $*" >>"$PODMAN_CALLS_FILE"
        return 0
    }
    export -f podman

    # Run main in a subshell to capture output and exit code
    set +e
    output=$(
        set -euo pipefail
        printf '%s' "testpass" | main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "localhost" \
            --target-site-name "mysite" \
            --user "testuser" \
            2>&1
    )
    local exit_code=$?
    set -e

    # Assert that main succeeded
    assertEquals "main should succeed" 0 "$exit_code"

    # Verify that localhost was replaced with host.containers.internal
    grep -q "podman run --rm -v relay:/opt/check-mk-relay/workdir localhost/checkmk_relay:checkmk_sync cmk-relay register --server host.containers.internal --site mysite --relay-alias test-relay --trust-cert --force --user testuser --password testpass" "$PODMAN_CALLS_FILE"
    assertTrue "podman run should use host.containers.internal instead of localhost" $?
}

# Test: Registration with 127.0.0.1 uses host.containers.internal
test_registration_127_0_0_1_uses_host_containers_internal() {
    # Mock podman to succeed and track all calls
    # shellcheck disable=SC2317
    podman() {
        echo "podman $*" >>"$PODMAN_CALLS_FILE"
        return 0
    }
    export -f podman

    # Run main in a subshell to capture output and exit code
    set +e
    output=$(
        set -euo pipefail
        printf '%s' "testpass" | main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "127.0.0.1" \
            --target-site-name "mysite" \
            --user "testuser" \
            2>&1
    )
    local exit_code=$?
    set -e

    # Assert that main succeeded
    assertEquals "main should succeed" 0 "$exit_code"

    # Verify that 127.0.0.1 was replaced with host.containers.internal
    grep -q "podman run --rm -v relay:/opt/check-mk-relay/workdir localhost/checkmk_relay:checkmk_sync cmk-relay register --server host.containers.internal --site mysite --relay-alias test-relay --trust-cert --force --user testuser --password testpass" "$PODMAN_CALLS_FILE"
    assertTrue "podman run should use host.containers.internal instead of 127.0.0.1" $?
}

# Test: Registration with 127.0.1.1 uses host.containers.internal
test_registration_127_0_1_1_uses_host_containers_internal() {
    # Mock podman to succeed and track all calls
    # shellcheck disable=SC2317
    podman() {
        echo "podman $*" >>"$PODMAN_CALLS_FILE"
        return 0
    }
    export -f podman

    # Run main in a subshell to capture output and exit code
    set +e
    output=$(
        set -euo pipefail
        printf '%s' "testpass" | main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "127.0.1.1" \
            --target-site-name "mysite" \
            --user "testuser" \
            2>&1
    )
    local exit_code=$?
    set -e

    # Assert that main succeeded
    assertEquals "main should succeed" 0 "$exit_code"

    # Verify that 127.0.1.1 was replaced with host.containers.internal
    grep -q "podman run --rm -v relay:/opt/check-mk-relay/workdir localhost/checkmk_relay:checkmk_sync cmk-relay register --server host.containers.internal --site mysite --relay-alias test-relay --trust-cert --force --user testuser --password testpass" "$PODMAN_CALLS_FILE"
    assertTrue "podman run should use host.containers.internal instead of 127.0.1.1" $?
}

# Test: Registration with ::1 uses host.containers.internal
test_registration_ipv6_localhost_uses_host_containers_internal() {
    # Mock podman to succeed and track all calls
    # shellcheck disable=SC2317
    podman() {
        echo "podman $*" >>"$PODMAN_CALLS_FILE"
        return 0
    }
    export -f podman

    # Run main in a subshell to capture output and exit code
    set +e
    output=$(
        set -euo pipefail
        printf '%s' "testpass" | main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "::1" \
            --target-site-name "mysite" \
            --user "testuser" \
            2>&1
    )
    local exit_code=$?
    set -e

    # Assert that main succeeded
    assertEquals "main should succeed" 0 "$exit_code"

    # Verify that ::1 was replaced with host.containers.internal
    grep -q "podman run --rm -v relay:/opt/check-mk-relay/workdir localhost/checkmk_relay:checkmk_sync cmk-relay register --server host.containers.internal --site mysite --relay-alias test-relay --trust-cert --force --user testuser --password testpass" "$PODMAN_CALLS_FILE"
    assertTrue "podman run should use host.containers.internal instead of ::1" $?
}

# Test: Registration with unresolvable address should fail
test_registration_unresolvable_address_fails() {
    # Override getent to simulate resolution failure
    # getent returns exit code 2 when it cannot resolve an address
    # shellcheck disable=SC2317
    getent() {
        if [[ "$1" == "ahosts" && "$2" == "unresolvable.invalid" ]]; then
            return 2 # Simulate resolution failure (no output)
        fi
        # For other calls, use the original mock
        builtin echo "192.168.1.1     STREAM $2"
        return 0
    }
    export -f getent

    # Mock podman to succeed and track all calls
    # shellcheck disable=SC2317
    podman() {
        echo "podman $*" >>"$PODMAN_CALLS_FILE"
        return 0
    }
    export -f podman

    # Run main in a subshell to capture output and exit code
    set +e
    output=$(
        set -euo pipefail
        printf '%s' "testpass" | main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "unresolvable.invalid" \
            --target-site-name "mysite" \
            --user "testuser" \
            2>&1
    )
    local exit_code=$?
    set -e

    # Assert that main exited with error
    assertNotEquals "main should exit with error for unresolvable address" 0 "$exit_code"

    # Assert that the error message contains the expected text
    echo "$output" | grep -q "Could not resolve address"
    assertTrue "Error message should mention resolution failure" $?
}

# shellcheck disable=SC1090
source "$UNIT_SH_SHUNIT2"
