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

    # Reset mock calls before each test
    MOCK_CALLS=()

    # Create temporary directory for test files
    TEST_DIR=$(mktemp -d)
    export CHECKMK_RELAY_DATA_DIR="${TEST_DIR}/opt/checkmk_relay"
    export CHECKMK_RELAY_BIN_DIR="${TEST_DIR}/usr/local/bin"
    export CHECKMK_RELAY_SYSTEMD_DIR="${TEST_DIR}/etc/systemd/system"
    export CHECKMK_RELAY_QUADLET_DIR="${TEST_DIR}/etc/containers/systemd"

    # Create file to track calls across subshells
    MOCK_CALLS_FILE="${TEST_DIR}/mock_calls.log"
    export MOCK_CALLS_FILE
    touch "$MOCK_CALLS_FILE"

    # Mock logging functions to suppress output
    # shellcheck disable=SC2317
    err() { :; }
    export -f info
    export -f warn
    export -f err
    export -f die
}

tearDown() {
    # Clean up temporary directory
    if [ -n "${TEST_DIR:-}" ] && [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
}

test_main_successful_call_order() {
    # Run main in a subshell as root
    set +e
    (
        set -euo pipefail
        # shellcheck disable=SC2317  # called indirectly via export -f
        get_euid() { echo 0; }
        export -f get_euid
        main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "server.example.com" \
            --target-site-name "mysite" \
            --token "testtoken" \
            2>/dev/null
    )
    local exit_code=$?
    set -e

    # Main should succeed
    assertEquals "main should exit successfully" 0 "$exit_code"

    # Load mock calls from file
    mapfile -t MOCK_CALLS <"$MOCK_CALLS_FILE"

    # Filter out echo and date calls (too noisy, from logging functions)
    local external_calls=()
    for call in "${MOCK_CALLS[@]}"; do
        [[ "$call" =~ ^echo ]] && continue
        [[ "$call" =~ ^date ]] && continue
        external_calls+=("$call")
    done

    # Expected calls in order (with patterns for dynamic values)
    local expected_calls=(
        "basename *" # Script name varies
        "command -v podman"
        "command -v systemctl"
        "mkdir -p */opt/checkmk_relay" # Temp dir varies
        "mkdir -p */usr/local/bin"
        "mkdir -p */etc/systemd/system"
        "mkdir -p */etc/containers/systemd"
        "chown 99000:99000 */opt/checkmk_relay/update-trigger.conf"
        "chmod 644 */opt/checkmk_relay/update-trigger.conf"
        "podman volume exists relay"
        "podman volume create relay"
        "podman pull docker.io/checkmk/check-mk-relay:1.0.0"
        "podman tag docker.io/checkmk/check-mk-relay:1.0.0 localhost/checkmk_relay:checkmk_sync"
        "podman run --rm --uidmap=0:99000:65536 --gidmap=0:99000:65536 -v relay:/opt/check-mk-relay/workdir:Z localhost/checkmk_relay:checkmk_sync test -f /opt/check-mk-relay/workdir/site_config.json"
        "podman run --rm --uidmap=0:99000:65536 --gidmap=0:99000:65536 --network=bridge -v relay:/opt/check-mk-relay/workdir:Z localhost/checkmk_relay:checkmk_sync cmk-relay register --server server.example.com --site mysite --relay-alias test-relay --trust-cert --token testtoken"
        "cat *" # Heredoc writes, path varies
        "chmod 755 *checkmk_relay-update-manager.sh"
        "cat *" # write_container_unit
        "cat *" # write_path_unit
        "cat *" # write_update_service_unit
        "systemctl daemon-reload"
        "sleep 2"
        "systemctl enable --now checkmk_relay-update-manager.path"
        "systemctl start checkmk_relay.service"
        "systemctl status checkmk_relay-update-manager.path --no-pager"
        "systemctl status checkmk_relay.service --no-pager"
    )

    # Verify we have the expected number of calls
    assertEquals "Number of external calls" "${#expected_calls[@]}" "${#external_calls[@]}"

    # Verify each call matches the expected pattern
    for i in "${!expected_calls[@]}"; do
        local expected="${expected_calls[$i]}"
        local actual="${external_calls[$i]}"

        # Use pattern matching for comparison
        # shellcheck disable=SC2053
        if [[ "$actual" == $expected ]]; then
            # Match - assertion passes
            assertTrue "Call $i matches: $expected" true
        else
            # No match - show what we got
            assertEquals "Call $i should match pattern" "$expected" "$actual"
        fi
    done
}

# shellcheck disable=SC1090
source "$UNIT_SH_SHUNIT2"
