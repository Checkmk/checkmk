#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Verify that install_relay.sh never writes credentials (token or password) to
# its stdout/stderr or to the podman call log, even when --verbose is active.
# Uses random-per-run secrets so coincidental substring matches are impossible.

oneTimeSetUp() {
    set +euo pipefail
    # shellcheck disable=SC1091
    MK_SOURCE_ONLY="true" source "${UNIT_SH_REPO_PATH}/omd/non-free/relay/install_relay.sh"
    set -euo pipefail
}

setUp() {
    # shellcheck source=tests/unit-shell/relay/mocks.sh
    source "${UNIT_SH_REPO_PATH}/tests/unit-shell/relay/mocks.sh"

    TEST_DIR=$(mktemp -d)
    export CHECKMK_RELAY_DATA_DIR="${TEST_DIR}/opt/checkmk_relay"
    export CHECKMK_RELAY_BIN_DIR="${TEST_DIR}/usr/local/bin"
    export CHECKMK_RELAY_SYSTEMD_DIR="${TEST_DIR}/etc/systemd/system"
    export CHECKMK_RELAY_QUADLET_DIR="${TEST_DIR}/etc/containers/systemd"

    PODMAN_CALLS_FILE="${TEST_DIR}/podman_calls.log"
    export PODMAN_CALLS_FILE
    touch "$PODMAN_CALLS_FILE"

    # shellcheck disable=SC2317
    get_euid() { echo 0; }
    export -f get_euid

    OS_RELEASE_FILE="${TEST_DIR}/os-release"
    export OS_RELEASE_FILE
    printf 'ID="ubuntu"\nVERSION_ID="24.04"\n' >"$OS_RELEASE_FILE"

    # Random credentials — unique per test run so any match is a genuine leak.
    # Hex-only format (od -tx1) guarantees no single quotes, spaces, or shell
    # metacharacters. The assertFalse patterns below embed these values inside
    # single-quoted shell expressions; they would misparse if either variable
    # contained a single quote.
    SECRET_TOKEN="tkn-$(head -c 12 /dev/urandom | od -An -tx1 | tr -d ' \n')-secret"
    SECRET_PASSWORD="pw-$(head -c 12 /dev/urandom | od -An -tx1 | tr -d ' \n')-secret"
    export SECRET_TOKEN SECRET_PASSWORD
}

tearDown() {
    if [ -n "${TEST_DIR:-}" ] && [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
}

# Helper: standard podman mock that simulates a relay that is not yet registered.
_mock_podman_success() {
    # shellcheck disable=SC2317
    podman() {
        echo "podman $*" >>"$PODMAN_CALLS_FILE"
        if [[ "$1" == "run" ]] && [[ "$*" == *"test -f"*"site_config.json"* ]]; then
            return 1
        fi
        return 0
    }
    export -f podman
}

# Token auth via --token-stdin (MSI/Windows path): token must not appear anywhere.
test_token_stdin_not_in_output_verbose() {
    _mock_podman_success

    set +e
    output=$(
        set -euo pipefail
        printf '%s\n' "$SECRET_TOKEN" | main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "server.example.com" \
            --target-site-name "mysite" \
            --token-stdin \
            --verbose \
            2>&1
    )
    local exit_code=$?
    set -e

    assertEquals "install should succeed" 0 "$exit_code"

    assertFalse "token must not appear in script output" \
        "printf '%s' '$output' | grep -qF '$SECRET_TOKEN'"
    assertFalse "token must not appear in podman call log" \
        "grep -qF '$SECRET_TOKEN' '$PODMAN_CALLS_FILE'"
    assertTrue "podman run should use --token-stdin" \
        "grep -q 'cmk-relay register.*--token-stdin' '$PODMAN_CALLS_FILE'"
}

# Password auth, verbose: password must not appear anywhere in output or podman calls.
test_password_not_in_output_verbose() {
    _mock_podman_success

    set +e
    output=$(
        set -euo pipefail
        printf '%s\n' "$SECRET_PASSWORD" | main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "server.example.com" \
            --target-site-name "mysite" \
            --user "testuser" \
            --verbose \
            2>&1
    )
    local exit_code=$?
    set -e

    assertEquals "install should succeed" 0 "$exit_code"

    # Password must not appear in script stdout/stderr
    assertFalse "password must not appear in script output" \
        "printf '%s' '$output' | grep -qF '$SECRET_PASSWORD'"

    # Password must not appear in podman argv (it is piped via stdin, not --password)
    assertFalse "password must not appear in podman call log" \
        "grep -qF '$SECRET_PASSWORD' '$PODMAN_CALLS_FILE'"

    # Sanity: --password flag absent (password went via stdin)
    assertFalse "podman run must not carry --password flag" \
        "grep -q 'cmk-relay register.*--password' '$PODMAN_CALLS_FILE'"
}

# Token passed via --token VALUE: must not leak into podman argv or script output.
test_token_arg_not_in_output_verbose() {
    _mock_podman_success

    set +e
    output=$(
        set -euo pipefail
        main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "server.example.com" \
            --target-site-name "mysite" \
            --token "$SECRET_TOKEN" \
            --verbose \
            2>&1
    )
    local exit_code=$?
    set -e

    assertEquals "install should succeed" 0 "$exit_code"

    assertFalse "token must not appear in script output" \
        "printf '%s' '$output' | grep -qF '$SECRET_TOKEN'"
    assertFalse "token must not appear in podman call log" \
        "grep -qF '$SECRET_TOKEN' '$PODMAN_CALLS_FILE'"
    assertTrue "podman run should use --token-stdin" \
        "grep -q 'cmk-relay register.*--token-stdin' '$PODMAN_CALLS_FILE'"
}

# shellcheck disable=SC1090
source "$UNIT_SH_SHUNIT2"
