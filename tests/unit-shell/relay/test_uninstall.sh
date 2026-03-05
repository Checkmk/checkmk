#!/bin/bash
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

oneTimeSetUp() {
    # Source the script under test (defines functions, does NOT call main or config)
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

    # Track calls across subshells
    MOCK_CALLS_FILE="${TEST_DIR}/mock_calls.log"
    export MOCK_CALLS_FILE
    touch "$MOCK_CALLS_FILE"

    # System mode requires root for uninstall
    # shellcheck disable=SC2317
    get_euid() { echo 0; }
    export -f get_euid

    # Suppress logging output
    # shellcheck disable=SC2317
    err() { :; }
    export -f err
    export -f info
    export -f warn
    export -f die
}

tearDown() {
    if [ -n "${TEST_DIR:-}" ] && [ -d "$TEST_DIR" ]; then
        /bin/rm -rf "$TEST_DIR"
    fi
}

# =============================================================================
# parse_args tests for --uninstall mode
# =============================================================================

test_parse_args_uninstall_mode() {
    # --uninstall should succeed without any install-specific args
    local result
    result=$(
        config
        parse_args --uninstall
        echo "${MODE}"
    )
    assertEquals "MODE should be uninstall" "uninstall" "$result"
}

test_parse_args_uninstall_keep_volume() {
    local result
    result=$(
        config
        parse_args --uninstall --keep-volume
        echo "${ARGS_KEEP_VOLUME}"
    )
    assertEquals "ARGS_KEEP_VOLUME should be true" "true" "$result"
}

test_parse_args_uninstall_remove_images() {
    local result
    result=$(
        config
        parse_args --uninstall --remove-images
        echo "${ARGS_REMOVE_IMAGES}"
    )
    assertEquals "ARGS_REMOVE_IMAGES should be true" "true" "$result"
}

# =============================================================================
# stop_services tests
# =============================================================================

test_uninstall_stops_services() {
    set +e
    (
        set -euo pipefail
        config
        stop_services
    )
    local exit_code=$?
    set -e

    assertEquals "stop_services should succeed" 0 "$exit_code"

    mapfile -t MOCK_CALLS <"$MOCK_CALLS_FILE"

    local found_relay=false found_path=false found_service=false
    for call in "${MOCK_CALLS[@]}"; do
        [[ "$call" == "systemctl stop checkmk_relay.service" ]] && found_relay=true
        [[ "$call" == "systemctl stop checkmk_relay-update-manager.path" ]] && found_path=true
        [[ "$call" == "systemctl stop checkmk_relay-update-manager.service" ]] && found_service=true
    done

    assertTrue "Should stop checkmk_relay.service" "$found_relay"
    assertTrue "Should stop checkmk_relay-update-manager.path" "$found_path"
    assertTrue "Should stop checkmk_relay-update-manager.service" "$found_service"
}

# =============================================================================
# disable_services tests
# =============================================================================

test_uninstall_disables_services() {
    set +e
    (
        set -euo pipefail
        config
        disable_services
    )
    local exit_code=$?
    set -e

    assertEquals "disable_services should succeed" 0 "$exit_code"

    mapfile -t MOCK_CALLS <"$MOCK_CALLS_FILE"

    local found_path=false found_service=false
    for call in "${MOCK_CALLS[@]}"; do
        [[ "$call" == "systemctl disable checkmk_relay-update-manager.path" ]] && found_path=true
        [[ "$call" == "systemctl disable checkmk_relay-update-manager.service" ]] && found_service=true
    done

    assertTrue "Should disable checkmk_relay-update-manager.path" "$found_path"
    assertTrue "Should disable checkmk_relay-update-manager.service" "$found_service"
}

# =============================================================================
# remove_files tests
# =============================================================================

test_uninstall_removes_files() {
    set +e
    (
        set -euo pipefail
        config
        remove_files
    )
    local exit_code=$?
    set -e

    assertEquals "remove_files should succeed" 0 "$exit_code"

    mapfile -t MOCK_CALLS <"$MOCK_CALLS_FILE"

    local found_update_script=false found_container=false
    local found_path_unit=false found_service_unit=false
    local p_script="rm -f *checkmk_relay-update-manager.sh"
    local p_container="rm -f *checkmk_relay.container"
    local p_path="rm -f *checkmk_relay-update-manager.path"
    local p_service="rm -f *checkmk_relay-update-manager.service"
    for call in "${MOCK_CALLS[@]}"; do
        # shellcheck disable=SC2053
        [[ "$call" == $p_script ]] && found_update_script=true
        # shellcheck disable=SC2053
        [[ "$call" == $p_container ]] && found_container=true
        # shellcheck disable=SC2053
        [[ "$call" == $p_path ]] && found_path_unit=true
        # shellcheck disable=SC2053
        [[ "$call" == $p_service ]] && found_service_unit=true
    done

    assertTrue "Should remove update script" "$found_update_script"
    assertTrue "Should remove container unit" "$found_container"
    assertTrue "Should remove path unit" "$found_path_unit"
    assertTrue "Should remove service unit" "$found_service_unit"
}

# =============================================================================
# remove_data_dirs tests
# =============================================================================

test_uninstall_removes_data_dirs() {
    set +e
    (
        set -euo pipefail
        config
        remove_data_dirs
    )
    local exit_code=$?
    set -e

    assertEquals "remove_data_dirs should succeed" 0 "$exit_code"

    mapfile -t MOCK_CALLS <"$MOCK_CALLS_FILE"

    local found_app_data=false
    local p="rm -rf *checkmk_relay"
    for call in "${MOCK_CALLS[@]}"; do
        # shellcheck disable=SC2053
        [[ "$call" == $p ]] && found_app_data=true
    done

    assertTrue "Should remove APP_DATA_DIR (checkmk_relay data dir)" "$found_app_data"
}

# =============================================================================
# reload_systemd tests
# =============================================================================

test_uninstall_reloads_systemd() {
    set +e
    (
        set -euo pipefail
        config
        reload_systemd
    )
    local exit_code=$?
    set -e

    assertEquals "reload_systemd should succeed" 0 "$exit_code"

    mapfile -t MOCK_CALLS <"$MOCK_CALLS_FILE"

    local found_reload=false
    for call in "${MOCK_CALLS[@]}"; do
        [[ "$call" == "systemctl daemon-reload" ]] && found_reload=true
    done

    assertTrue "Should call systemctl daemon-reload" "$found_reload"
}

# =============================================================================
# podman resource tests
# =============================================================================

test_uninstall_removes_volume_by_default() {
    set +e
    (
        set -euo pipefail
        config
        ARGS_KEEP_VOLUME=""
        ARGS_REMOVE_IMAGES=""
        remove_podman_resources
    )
    local exit_code=$?
    set -e

    assertEquals "remove_podman_resources should succeed" 0 "$exit_code"

    mapfile -t MOCK_CALLS <"$MOCK_CALLS_FILE"

    local found_volume_rm=false
    for call in "${MOCK_CALLS[@]}"; do
        [[ "$call" == "podman volume rm relay" ]] && found_volume_rm=true
    done

    assertTrue "Should remove podman volume 'relay' by default" "$found_volume_rm"
}

test_uninstall_keep_volume_flag() {
    set +e
    (
        set -euo pipefail
        config
        ARGS_KEEP_VOLUME="true"
        ARGS_REMOVE_IMAGES=""
        remove_podman_resources
    )
    local exit_code=$?
    set -e

    assertEquals "remove_podman_resources with --keep-volume should succeed" 0 "$exit_code"

    mapfile -t MOCK_CALLS <"$MOCK_CALLS_FILE"

    local found_volume_rm=false
    for call in "${MOCK_CALLS[@]}"; do
        [[ "$call" == "podman volume rm relay" ]] && found_volume_rm=true
    done

    assertFalse "Should NOT remove podman volume when --keep-volume is set" "$found_volume_rm"
}

test_uninstall_remove_images_flag() {
    set +e
    (
        set -euo pipefail
        config
        ARGS_KEEP_VOLUME="true"
        ARGS_REMOVE_IMAGES="true"
        remove_podman_resources
    )
    local exit_code=$?
    set -e

    assertEquals "remove_podman_resources with --remove-images should succeed" 0 "$exit_code"

    mapfile -t MOCK_CALLS <"$MOCK_CALLS_FILE"

    local found_rmi=false
    for call in "${MOCK_CALLS[@]}"; do
        [[ "$call" == "podman rmi localhost/checkmk_relay:checkmk_sync" ]] && found_rmi=true
    done

    assertTrue "Should remove local image when --remove-images is set" "$found_rmi"
}

# =============================================================================
# Idempotency test
# =============================================================================

test_uninstall_idempotent() {
    # Running uninstall when services/files don't exist should still exit 0
    set +e
    (
        set -euo pipefail
        main --uninstall --keep-volume 2>/dev/null
    )
    local exit_code=$?
    set -e

    assertEquals "uninstall should exit 0 even when nothing to remove" 0 "$exit_code"
}

# =============================================================================
# Full call order test
# =============================================================================

test_uninstall_full_call_order() {
    set +e
    (
        set -euo pipefail
        main --uninstall 2>/dev/null
    )
    local exit_code=$?
    set -e

    assertEquals "main --uninstall should exit successfully" 0 "$exit_code"

    mapfile -t MOCK_CALLS <"$MOCK_CALLS_FILE"

    # Filter out echo and date calls (from logging functions)
    local external_calls=()
    for call in "${MOCK_CALLS[@]}"; do
        [[ "$call" =~ ^echo ]] && continue
        [[ "$call" =~ ^date ]] && continue
        external_calls+=("$call")
    done

    # Expected calls in order (with glob patterns for dynamic path values)
    local expected_calls=(
        "basename *"
        "systemctl stop checkmk_relay.service"
        "systemctl stop checkmk_relay-update-manager.path"
        "systemctl stop checkmk_relay-update-manager.service"
        "systemctl disable checkmk_relay.service"
        "systemctl disable checkmk_relay-update-manager.path"
        "systemctl disable checkmk_relay-update-manager.service"
        "rm -f *checkmk_relay-update-manager.sh"
        "rm -f *checkmk_relay.container"
        "rm -f *checkmk_relay-update-manager.path"
        "rm -f *checkmk_relay-update-manager.service"
        "rm -rf *checkmk_relay"
        "systemctl daemon-reload"
        "podman volume rm relay"
    )

    # Verify we have the expected number of calls
    assertEquals "Number of external calls" "${#expected_calls[@]}" "${#external_calls[@]}"

    # Verify each call matches the expected pattern
    for i in "${!expected_calls[@]}"; do
        local expected="${expected_calls[$i]}"
        local actual="${external_calls[$i]:-}"

        # Use pattern matching for comparison (SC2053: unquoted rhs is intentional for glob)
        # shellcheck disable=SC2053
        if [[ "$actual" == $expected ]]; then
            assertTrue "Call $i matches: $expected" true
        else
            assertEquals "Call $i should match pattern '$expected'" "$expected" "$actual"
        fi
    done
}

# shellcheck disable=SC1090
source "$UNIT_SH_SHUNIT2"
