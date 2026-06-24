#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Tests for the --update-systemd mode, focused on network-mode handling:
#   - preserve_network_mode() reads the on-disk .container so a regenerated unit
#     keeps the relay on its current network, unless --use-host-network forces host.

oneTimeSetUp() {
    # shellcheck disable=SC1091
    MK_SOURCE_ONLY="true" source "${UNIT_SH_REPO_PATH}/omd/non-free/relay/install_relay.sh"

    TEST_DIR=$(mktemp -d)
    export CHECKMK_RELAY_DATA_DIR="${TEST_DIR}/opt/checkmk_relay"
    export CHECKMK_RELAY_BIN_DIR="${TEST_DIR}/usr/local/bin"
    export CHECKMK_RELAY_SYSTEMD_DIR="${TEST_DIR}/etc/systemd/system"
    export CHECKMK_RELAY_QUADLET_DIR="${TEST_DIR}/etc/containers/systemd"

    # Initialize config (sets readonly vars from the CHECKMK_RELAY_* env vars above)
    config

    mkdir -p "$QUADLET_DIR"
    mkdir -p "$SYSTEMD_SYSTEM_DIR"
    mkdir -p "$APP_DATA_DIR"
    mkdir -p "$(dirname "$UPDATE_SCRIPT_PATH")"
    echo "1.0.0" >"$TRIGGER_FILE"

    # Suppress log output during tests
    # shellcheck disable=SC2317
    info() { :; }
}

oneTimeTearDown() {
    [ -d "${TEST_DIR:-}" ] && rm -rf "$TEST_DIR"
    return 0
}

setUp() {
    # Each test starts with the flag unset (the default after parse_args) and a
    # clean quadlet dir; tests opt into a starting .container and/or flag value.
    ARGS_USE_HOST_NETWORK=""
    mkdir -p "$QUADLET_DIR"
    rm -f "${QUADLET_DIR}/checkmk_relay.container"
}

# === preserve_network_mode() ===

test_preserve_detects_host_when_flag_unset() {
    _write_container_with_network "host"
    preserve_network_mode
    assertEquals "host .container should set ARGS_USE_HOST_NETWORK=true" \
        "true" "$ARGS_USE_HOST_NETWORK"
}

test_preserve_keeps_bridge_when_flag_unset() {
    _write_container_with_network "bridge"
    preserve_network_mode
    assertEquals "bridge .container should leave ARGS_USE_HOST_NETWORK empty" \
        "" "$ARGS_USE_HOST_NETWORK"
}

test_preserve_does_not_downgrade_explicit_flag() {
    # Operator passed --use-host-network even though the on-disk unit is bridge.
    ARGS_USE_HOST_NETWORK="true"
    _write_container_with_network "bridge"
    preserve_network_mode
    assertEquals "explicit --use-host-network must not be downgraded" \
        "true" "$ARGS_USE_HOST_NETWORK"
}

test_preserve_is_noop_when_no_container_unit() {
    # No .container on disk (rare): must not error under set -euo pipefail.
    preserve_network_mode
    assertEquals "missing .container should succeed" 0 $?
    assertEquals "missing .container should leave flag empty" \
        "" "$ARGS_USE_HOST_NETWORK"
}

# === preserve_network_mode() + regeneration (the update-systemd sequence) ===

test_update_preserves_host_network() {
    _write_container_with_network "host"
    preserve_network_mode
    write_container_unit
    grep -q "^Network=host" "${QUADLET_DIR}/checkmk_relay.container"
    assertEquals "regenerated unit should keep Network=host" 0 $?
}

test_update_preserves_bridge_network() {
    _write_container_with_network "bridge"
    preserve_network_mode
    write_container_unit
    grep -q "^Network=bridge" "${QUADLET_DIR}/checkmk_relay.container"
    assertEquals "regenerated unit should keep Network=bridge" 0 $?
}

test_update_forces_host_with_use_host_network_flag() {
    # --use-host-network flips a previously-bridge relay to host on update.
    ARGS_USE_HOST_NETWORK="true"
    _write_container_with_network "bridge"
    preserve_network_mode
    write_container_unit
    grep -q "^Network=host" "${QUADLET_DIR}/checkmk_relay.container"
    assertEquals "regenerated unit should use Network=host when flag is set" 0 $?
}

# === check_relay_installed() — guard against updating an uninstalled host ===

test_check_relay_installed_passes_when_container_present() {
    _write_container_with_network "host"
    check_relay_installed
    assertEquals "existing .container should pass the guard" 0 $?
}

test_check_relay_installed_fails_when_no_container() {
    # setUp removed the .container: --update-systemd must refuse to proceed.
    (check_relay_installed 2>/dev/null)
    assertEquals "missing .container should fail fast" 1 $?
}

# === ensure_infra_dirs() — must never touch the version trigger file ===

test_ensure_infra_dirs_leaves_trigger_file_untouched() {
    # The version trigger is the relay's image version; --update-systemd touches
    # host infra only, so ensure_infra_dirs must not rewrite it.
    echo "9.9.9" >"$TRIGGER_FILE"
    ensure_infra_dirs
    assertEquals "trigger file content must be unchanged" \
        "9.9.9" "$(cat "$TRIGGER_FILE")"
}

# === Helpers ===

_write_container_with_network() {
    # $1 = host|bridge — minimal .container carrying just the Network directive
    # that preserve_network_mode reads.
    printf '[Container]\nNetwork=%s\n' "$1" >"${QUADLET_DIR}/checkmk_relay.container"
}

# shellcheck disable=SC1090
source "$UNIT_SH_SHUNIT2"
