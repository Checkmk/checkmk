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

    # Reset mock calls before each test
    MOCK_CALLS=()

    # Create temporary directory for test files
    TEST_DIR=$(mktemp -d)
    export XDG_CONFIG_HOME="${TEST_DIR}/.config"
    export XDG_DATA_HOME="${TEST_DIR}/.local/share"
    export HOME="${TEST_DIR}"
    export USER="testuser"

    # Create file to track calls across subshells
    MOCK_CALLS_FILE="${TEST_DIR}/mock_calls.log"
    export MOCK_CALLS_FILE
    # Make sure parent dir exists (it should since TEST_DIR was just created)
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
    # Run main in a subshell
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
        "loginctl enable-linger *" # Username varies
        "mkdir -p */checkmk_relay" # Temp dir varies
        "mkdir -p */.local/bin"
        "mkdir -p */.config/systemd/user"
        "mkdir -p */.config/containers/systemd"
        "chmod 644 */checkmk_relay/update-trigger.conf"
        "podman volume exists relay"
        "podman volume create relay"
        "podman pull docker.io/checkmk/check-mk-relay:1.0.0"
        "podman tag docker.io/checkmk/check-mk-relay:1.0.0 localhost/checkmk_relay:checkmk_sync"
        "podman run --rm -v relay:/opt/check-mk-relay/workdir localhost/checkmk_relay:checkmk_sync cmk-relay register --server server.example.com --site mysite --relay-alias test-relay --trust-cert --force --user testuser --password testpass"
        "cat *" # Heredoc writes, path varies
        "chmod 755 *checkmk_relay-update-manager.sh"
        "cat *" # More heredoc writes
        "cat *"
        "cat *"
        "systemctl --user daemon-reload"
        "sleep 2"
        "systemctl --user enable --now checkmk_relay-update-manager.path"
        "systemctl --user enable --now checkmk_relay-update-manager.service"
        "systemctl --user start checkmk_relay.service"
        "systemctl --user status checkmk_relay-update-manager.path --no-pager"
        "systemctl --user status checkmk_relay.service --no-pager"
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
