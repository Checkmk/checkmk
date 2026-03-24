#!/bin/bash
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the
# terms and conditions defined in the file COPYING, which is part of this
# source code package.

oneTimeSetUp() {
    set +euo pipefail
    # shellcheck disable=SC1091
    MK_SOURCE_ONLY="true" source "${UNIT_SH_REPO_PATH}/omd/non-free/relay/install_relay.sh"
    set -euo pipefail
}

setUp() {
    # shellcheck source=tests/unit-shell/relay/mocks.sh
    source "${UNIT_SH_REPO_PATH}/tests/unit-shell/relay/mocks.sh"
}

# Test: user namespaces enabled (value > 0) → check passes silently
test_user_namespaces_enabled_passes() {
    # shellcheck disable=SC2317
    _get_max_user_namespaces() { echo "15000"; }
    export -f _get_max_user_namespaces

    set +e
    output=$(check_user_namespaces 2>&1)
    local exit_code=$?
    set -e

    assertEquals "should succeed when user namespaces are enabled" 0 "$exit_code"
}

# Test: user namespaces disabled (value = 0) → check fails with message telling user to enable them
test_user_namespaces_disabled_fails() {
    # shellcheck disable=SC2317
    _get_max_user_namespaces() { echo "0"; }
    export -f _get_max_user_namespaces

    set +e
    output=$(check_user_namespaces 2>&1)
    local exit_code=$?
    set -e

    assertNotEquals "should fail when user.max_user_namespaces=0" 0 "$exit_code"
    echo "$output" | grep -qi "enable user namespaces"
    assertTrue "Error message should tell the user to enable user namespaces" $?
}

# Test: /proc file unreadable → check fails with descriptive error
test_user_namespaces_unreadable_fails() {
    # shellcheck disable=SC2317
    _get_max_user_namespaces() { echo ""; }
    export -f _get_max_user_namespaces

    set +e
    output=$(check_user_namespaces 2>&1)
    local exit_code=$?
    set -e

    assertNotEquals "should fail when max_user_namespaces cannot be read" 0 "$exit_code"
    echo "$output" | grep -q "Could not read"
    assertTrue "Error message should mention the read failure" $?
}

# shellcheck disable=SC1090
source "$UNIT_SH_SHUNIT2"
