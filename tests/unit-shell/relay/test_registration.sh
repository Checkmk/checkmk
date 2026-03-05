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

    # Create a file to track podman calls
    PODMAN_CALLS_FILE="${TEST_DIR}/podman_calls.log"
    export PODMAN_CALLS_FILE
    touch "$PODMAN_CALLS_FILE"

    # System mode requires root
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

# Test: Registration fails (podman run fails)
# If podman run fails during registration, main should exit with error
test_registration_fails() {
    # Mock podman to fail on 'run' with register arguments but track all calls
    # shellcheck disable=SC2317
    podman() {
        echo "podman $*" >>"$PODMAN_CALLS_FILE"
        if [[ "$1" == "run" ]] && [[ "$*" == *"test -f"*"site_config.json"* ]]; then
            return 1 # Relay not yet registered
        elif [[ "$1" == "run" ]] && [[ "$*" == *"cmk-relay register"* ]]; then
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
        main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "server.example.com" \
            --target-site-name "mysite" \
            --token "testtoken" \
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

    # Verify the arguments to podman run for registration (system mode: --uidmap, --gidmap, --network=bridge)
    grep -q "podman run --rm --uidmap=0:99000:65536 --gidmap=0:99000:65536 --network=bridge -v relay:/opt/check-mk-relay/workdir:Z localhost/checkmk_relay:checkmk_sync cmk-relay register --server server.example.com --site mysite --relay-alias test-relay --trust-cert --token testtoken" "$PODMAN_CALLS_FILE"
    assertTrue "podman run should have been called with correct registration arguments" $?
}

# Test: Registration with loopback address emits a warning but still uses bridge by default
test_registration_localhost_warns_about_loopback() {
    # shellcheck disable=SC2317
    podman() {
        echo "podman $*" >>"$PODMAN_CALLS_FILE"
        if [[ "$1" == "run" ]] && [[ "$*" == *"test -f"*"site_config.json"* ]]; then
            return 1 # Relay not yet registered
        fi
        return 0
    }
    export -f podman

    # Override warn to capture warning messages
    # shellcheck disable=SC2317
    warn() { echo "WARNING: $*" >&2; }
    export -f warn

    set +e
    output=$(
        set -euo pipefail
        main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "localhost" \
            --target-site-name "mysite" \
            --token "testtoken" \
            2>&1
    )
    local exit_code=$?
    set -e

    assertEquals "main should succeed" 0 "$exit_code"

    # Default is bridge even for loopback — user must opt in with --use-host-network
    grep -q "podman run --rm --uidmap=0:99000:65536 --gidmap=0:99000:65536 --network=bridge -v relay:/opt/check-mk-relay/workdir:Z localhost/checkmk_relay:checkmk_sync cmk-relay register --server localhost --site mysite --relay-alias test-relay --trust-cert --token testtoken" "$PODMAN_CALLS_FILE"
    assertTrue "podman run should use --network=bridge by default" $?

    # A warning should be emitted about the loopback address
    echo "$output" | grep -q "loopback"
    assertTrue "Warning should mention loopback address" $?
}

# Test: Registration with loopback:port emits a warning but still uses bridge by default
test_registration_loopback_with_port_warns() {
    # shellcheck disable=SC2317
    podman() {
        echo "podman $*" >>"$PODMAN_CALLS_FILE"
        if [[ "$1" == "run" ]] && [[ "$*" == *"test -f"*"site_config.json"* ]]; then
            return 1 # Relay not yet registered
        fi
        return 0
    }
    export -f podman

    # Override warn to capture warning messages
    # shellcheck disable=SC2317
    warn() { echo "WARNING: $*" >&2; }
    export -f warn

    set +e
    output=$(
        set -euo pipefail
        printf '%s' "testpass" | main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "localhost:8000" \
            --target-site-name "mysite" \
            --user "testuser" \
            2>&1
    )
    local exit_code=$?
    set -e

    assertEquals "main should succeed" 0 "$exit_code"

    grep -q "podman run --rm --uidmap=0:99000:65536 --gidmap=0:99000:65536 --network=bridge -v relay:/opt/check-mk-relay/workdir:Z localhost/checkmk_relay:checkmk_sync cmk-relay register --server localhost:8000 --site mysite --relay-alias test-relay --trust-cert --user testuser --password testpass" "$PODMAN_CALLS_FILE"
    assertTrue "podman run should use --network=bridge by default" $?

    echo "$output" | grep -q "loopback"
    assertTrue "Warning should mention loopback address" $?
}

# Test: Registration with remote host:port uses --network=bridge, passes host:port unchanged
test_registration_remote_host_with_port_uses_network_bridge() {
    # shellcheck disable=SC2317
    podman() {
        echo "podman $*" >>"$PODMAN_CALLS_FILE"
        if [[ "$1" == "run" ]] && [[ "$*" == *"test -f"*"site_config.json"* ]]; then
            return 1 # Relay not yet registered
        fi
        return 0
    }
    export -f podman

    set +e
    output=$(
        set -euo pipefail
        printf '%s' "testpass" | main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "192.168.122.1:8000" \
            --target-site-name "mysite" \
            --user "testuser" \
            2>&1
    )
    local exit_code=$?
    set -e

    assertEquals "main should succeed" 0 "$exit_code"

    grep -q "podman run --rm --uidmap=0:99000:65536 --gidmap=0:99000:65536 --network=bridge -v relay:/opt/check-mk-relay/workdir:Z localhost/checkmk_relay:checkmk_sync cmk-relay register --server 192.168.122.1:8000 --site mysite --relay-alias test-relay --trust-cert --user testuser --password testpass" "$PODMAN_CALLS_FILE"
    assertTrue "podman run should use --network=bridge for non-loopback host" $?
}

# Test: Registration with --use-host-network forces host networking
test_registration_use_host_network_flag() {
    # shellcheck disable=SC2317
    podman() {
        echo "podman $*" >>"$PODMAN_CALLS_FILE"
        if [[ "$1" == "run" ]] && [[ "$*" == *"test -f"*"site_config.json"* ]]; then
            return 1 # Relay not yet registered
        fi
        return 0
    }
    export -f podman

    set +e
    output=$(
        set -euo pipefail
        main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "server.example.com" \
            --target-site-name "mysite" \
            --token "testtoken" \
            --use-host-network \
            2>&1
    )
    local exit_code=$?
    set -e

    assertEquals "main should succeed" 0 "$exit_code"

    grep -q "podman run --rm --uidmap=0:99000:65536 --gidmap=0:99000:65536 --network=host -v relay:/opt/check-mk-relay/workdir:Z localhost/checkmk_relay:checkmk_sync cmk-relay register --server server.example.com --site mysite --relay-alias test-relay --trust-cert --token testtoken" "$PODMAN_CALLS_FILE"
    assertTrue "podman run should use --network=host when --use-host-network is set" $?
}

# Test: Registration with unresolvable address should fail
test_registration_unresolvable_address_fails() {
    # Override getent to simulate resolution failure
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

    # shellcheck disable=SC2317
    podman() {
        echo "podman $*" >>"$PODMAN_CALLS_FILE"
        if [[ "$1" == "run" ]] && [[ "$*" == *"test -f"*"site_config.json"* ]]; then
            return 1 # Relay not yet registered
        fi
        return 0
    }
    export -f podman

    set +e
    output=$(
        set -euo pipefail
        main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "unresolvable.invalid" \
            --target-site-name "mysite" \
            --token "testtoken" \
            2>&1
    )
    local exit_code=$?
    set -e

    assertNotEquals "main should exit with error for unresolvable address" 0 "$exit_code"

    echo "$output" | grep -q "Could not resolve address"
    assertTrue "Error message should mention resolution failure" $?
}

# Test: main aborts when relay is already registered and no --force is provided
test_registration_aborts_when_already_registered_without_force() {
    # Mock podman: simulate that site_config.json exists in the volume
    # shellcheck disable=SC2317
    podman() {
        echo "podman $*" >>"$PODMAN_CALLS_FILE"
        if [[ "$1" == "run" ]] && [[ "$*" == *"test -f"*"site_config.json"* ]]; then
            return 0 # Simulate: file exists → relay already registered
        fi
        return 0
    }
    export -f podman

    # Run main in a subshell without --force
    set +e
    output=$(
        set -euo pipefail
        main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "server.example.com" \
            --target-site-name "mysite" \
            --token "testtoken" \
            2>&1
    )
    local exit_code=$?
    set -e

    # Assert that main exited with error
    assertNotEquals "main should exit with error when relay is already registered" 0 "$exit_code"

    # Assert that the error message mentions the problem and --force
    echo "$output" | grep -q "already registered"
    assertTrue "Error message should mention 'already registered'" $?

    echo "$output" | grep -q "\-\-force"
    assertTrue "Error message should mention '--force'" $?
}

# Test: main succeeds when relay is already registered and --force is provided
test_registration_force_flag_bypasses_already_registered_check() {
    # Mock podman: simulate that site_config.json exists in the volume
    # shellcheck disable=SC2317
    podman() {
        echo "podman $*" >>"$PODMAN_CALLS_FILE"
        if [[ "$1" == "run" ]] && [[ "$*" == *"test -f"*"site_config.json"* ]]; then
            return 0 # Simulate: file exists → relay already registered
        fi
        return 0
    }
    export -f podman

    # Run main in a subshell with --force
    set +e
    output=$(
        set -euo pipefail
        main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "server.example.com" \
            --target-site-name "mysite" \
            --token "testtoken" \
            --force \
            2>&1
    )
    local exit_code=$?
    set -e

    # Assert that main succeeded despite relay being already registered
    assertEquals "main should succeed when --force is provided" 0 "$exit_code"
}

# Test: Registration with --force passes --force to podman run
test_registration_force_flag_is_forwarded_to_podman_run() {
    # Mock podman to succeed and track all calls
    # shellcheck disable=SC2317
    podman() {
        echo "podman $*" >>"$PODMAN_CALLS_FILE"
        if [[ "$1" == "run" ]] && [[ "$*" == *"test -f"*"site_config.json"* ]]; then
            return 1 # Relay not yet registered
        fi
        return 0
    }
    export -f podman

    # Run main in a subshell with --force flag
    set +e
    output=$(
        set -euo pipefail
        main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "server.example.com" \
            --target-site-name "mysite" \
            --token "testtoken" \
            --force \
            2>&1
    )
    local exit_code=$?
    set -e

    # Assert that main succeeded
    assertEquals "main should succeed" 0 "$exit_code"

    # Verify that --force was forwarded to the podman run command (system mode: --uidmap, --gidmap, --network=bridge)
    grep -q "podman run --rm --uidmap=0:99000:65536 --gidmap=0:99000:65536 --network=bridge -v relay:/opt/check-mk-relay/workdir:Z localhost/checkmk_relay:checkmk_sync cmk-relay register --server server.example.com --site mysite --relay-alias test-relay --trust-cert --force --token testtoken" "$PODMAN_CALLS_FILE"
    assertTrue "podman run should have been called with --force" $?
}

# shellcheck disable=SC1090
source "$UNIT_SH_SHUNIT2"
