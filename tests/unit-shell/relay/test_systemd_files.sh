#!/bin/bash
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

oneTimeSetUp() {
    # shellcheck disable=SC1091
    MK_SOURCE_ONLY="true" source "${UNIT_SH_REPO_PATH}/omd/non-free/relay/install_relay.sh"

    # Create temporary directory for test files
    TEST_DIR=$(mktemp -d)
    export CHECKMK_RELAY_DATA_DIR="${TEST_DIR}/opt/checkmk_relay"
    export CHECKMK_RELAY_BIN_DIR="${TEST_DIR}/usr/local/bin"
    export CHECKMK_RELAY_SYSTEMD_DIR="${TEST_DIR}/etc/systemd/system"
    export CHECKMK_RELAY_QUADLET_DIR="${TEST_DIR}/etc/containers/systemd"

    # Initialize config (sets readonly vars using the CHECKMK_RELAY_* env vars above)
    config

    # Create necessary directories
    mkdir -p "$QUADLET_DIR"
    mkdir -p "$SYSTEMD_SYSTEM_DIR"
    mkdir -p "$APP_DATA_DIR"
    mkdir -p "$(dirname "$UPDATE_SCRIPT_PATH")"

    # Create trigger file
    echo "1.0.0" >"$TRIGGER_FILE"

    # Mock info function to suppress output during tests
    # shellcheck disable=SC2317
    info() { :; }

    # write_container_unit calls get_network_mode (reads ARGS_USE_HOST_NETWORK) and
    # is_loopback (reads ARGS_TARGET_SERVER, getent, ip) — initialize all to avoid
    # unbound variable errors under set -euo pipefail
    ARGS_TARGET_SERVER="server.example.com"
    ARGS_VERBOSE=""
    ARGS_USE_HOST_NETWORK="" # unset = bridge (default); not under test here

    # shellcheck disable=SC2317
    getent() {
        builtin echo "192.168.1.1 STREAM $2"
    }
    # shellcheck disable=SC2317
    ip() {
        builtin echo "1: lo    inet 127.0.0.1/8 scope host lo"
        builtin echo "1: lo    inet6 ::1/128 scope host"
    }

    # Generate the systemd files
    write_systemd_units
}

oneTimeTearDown() {
    # Clean up temporary directory
    [ -d "${TEST_DIR:-}" ] && rm -rf "$TEST_DIR"
    return 0
}

# === Container Unit Tests ===

test_container_unit_file_exists() {
    local file_path="${QUADLET_DIR}/checkmk_relay.container"
    assertTrue "Container unit file should exist" "[ -f '$file_path' ]"
}

test_container_unit_not_in_user_config_dir() {
    assertFalse "Container unit must not be in a user config dir" \
        "[ -f '${TEST_DIR}/.config/containers/systemd/checkmk_relay.container' ]"
}

test_container_unit_has_unit_section() {
    local file_path="${QUADLET_DIR}/checkmk_relay.container"
    grep -q "^\[Unit\]" "$file_path"
    assertEquals "Container unit should have [Unit] section" 0 $?
}

test_container_unit_has_container_section() {
    local file_path="${QUADLET_DIR}/checkmk_relay.container"
    grep -q "^\[Container\]" "$file_path"
    assertEquals "Container unit should have [Container] section" 0 $?
}

test_container_unit_has_service_section() {
    local file_path="${QUADLET_DIR}/checkmk_relay.container"
    grep -q "^\[Service\]" "$file_path"
    assertEquals "Container unit should have [Service] section" 0 $?
}

test_container_unit_has_install_section() {
    local file_path="${QUADLET_DIR}/checkmk_relay.container"
    grep -q "^\[Install\]" "$file_path"
    assertEquals "Container unit should have [Install] section" 0 $?
}

test_container_unit_description() {
    local file_path="${QUADLET_DIR}/checkmk_relay.container"
    grep -q "^Description=Checkmk Relay Container" "$file_path"
    assertEquals "Container unit should have correct description" 0 $?
}

test_container_unit_after_network() {
    local file_path="${QUADLET_DIR}/checkmk_relay.container"
    grep -q "^After=network-online.target" "$file_path"
    assertEquals "Container unit should start after network-online.target" 0 $?
}

test_container_unit_container_name() {
    local file_path="${QUADLET_DIR}/checkmk_relay.container"
    grep -q "^ContainerName=checkmk_relay-container" "$file_path"
    assertEquals "Container unit should have correct container name" 0 $?
}

test_container_unit_image() {
    local file_path="${QUADLET_DIR}/checkmk_relay.container"
    grep -q "^Image=${LOCAL_TAG_NAME}" "$file_path"
    assertEquals "Container unit should reference local tag" 0 $?
}

test_container_unit_auto_update() {
    local file_path="${QUADLET_DIR}/checkmk_relay.container"
    grep -q "^AutoUpdate=local" "$file_path"
    assertEquals "Container unit should have AutoUpdate=local" 0 $?
}

test_container_unit_log_driver_journald() {
    local file_path="${QUADLET_DIR}/checkmk_relay.container"
    grep -q "^LogDriver=journald" "$file_path"
    assertEquals "Container unit should use journald log driver" 0 $?
}

test_container_unit_has_uidmap() {
    grep -q "^UIDMap=" "${QUADLET_DIR}/checkmk_relay.container"
    assertEquals "Container unit should have UIDMap directive" 0 $?
}

test_container_unit_has_gidmap() {
    grep -q "^GIDMap=" "${QUADLET_DIR}/checkmk_relay.container"
    assertEquals "Container unit should have GIDMap directive" 0 $?
}

test_container_unit_uidmap_maps_root_to_99000() {
    grep -q "^UIDMap=0:99000:65536" "${QUADLET_DIR}/checkmk_relay.container"
    assertEquals "UIDMap should map container root to host UID 99000" 0 $?
}

test_container_unit_gidmap_maps_root_to_99000() {
    grep -q "^GIDMap=0:99000:65536" "${QUADLET_DIR}/checkmk_relay.container"
    assertEquals "GIDMap should map container root to host GID 99000" 0 $?
}

test_container_unit_network_bridge_for_remote() {
    # Remote target server should use Network=bridge
    grep -q "^Network=bridge" "${QUADLET_DIR}/checkmk_relay.container"
    assertEquals "Container unit should use Network=bridge for remote target" 0 $?
}

test_container_unit_exec() {
    local file_path="${QUADLET_DIR}/checkmk_relay.container"
    grep -q "^Exec=sh -c 'cmk-relay daemon'" "$file_path"
    assertEquals "Container unit should execute cmk-relay daemon" 0 $?
}

test_container_unit_trigger_volume() {
    local file_path="${QUADLET_DIR}/checkmk_relay.container"
    grep -q "^Volume=${TRIGGER_FILE}:/opt/check-mk-relay/workdir/site-version.txt:rw,Z" "$file_path"
    assertEquals "Container unit should mount trigger file volume with SELinux label" 0 $?
}

test_container_unit_relay_volume() {
    local file_path="${QUADLET_DIR}/checkmk_relay.container"
    grep -q "^Volume=relay:/opt/check-mk-relay/workdir:rw,Z" "$file_path"
    assertEquals "Container unit should mount relay volume with SELinux label" 0 $?
}

test_container_unit_restart_always() {
    local file_path="${QUADLET_DIR}/checkmk_relay.container"
    grep -q "^Restart=always" "$file_path"
    assertEquals "Container unit should have Restart=always" 0 $?
}

test_container_unit_restart_sec() {
    local file_path="${QUADLET_DIR}/checkmk_relay.container"
    grep -q "^RestartSec=10" "$file_path"
    assertEquals "Container unit should have RestartSec=10" 0 $?
}

test_container_unit_wanted_by_multi_user_target() {
    local file_path="${QUADLET_DIR}/checkmk_relay.container"
    grep -q "^WantedBy=multi-user.target" "$file_path"
    assertEquals "Container unit should be wanted by multi-user.target" 0 $?
}

# === Path Unit Tests ===

test_path_unit_in_system_dir() {
    assertTrue "Path unit should be in system systemd dir" \
        "[ -f '${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.path' ]"
}

test_path_unit_has_unit_section() {
    local file_path="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.path"
    grep -q "^\[Unit\]" "$file_path"
    assertEquals "Path unit should have [Unit] section" 0 $?
}

test_path_unit_has_path_section() {
    local file_path="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.path"
    grep -q "^\[Path\]" "$file_path"
    assertEquals "Path unit should have [Path] section" 0 $?
}

test_path_unit_has_install_section() {
    local file_path="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.path"
    grep -q "^\[Install\]" "$file_path"
    assertEquals "Path unit should have [Install] section" 0 $?
}

test_path_unit_description() {
    local file_path="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.path"
    grep -q "^Description=Monitor Checkmk Relay Version File" "$file_path"
    assertEquals "Path unit should have correct description" 0 $?
}

test_path_unit_no_binds_to() {
    local file_path="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.path"
    # BindsTo= would stop the path unit whenever the relay restarts (e.g. after
    # podman-auto-update), permanently killing the update watcher. Must not be present.
    # shellcheck disable=SC2251
    ! grep -q "^BindsTo=" "$file_path"
    assertEquals "Path unit must not use BindsTo= (breaks across container restarts)" 0 $?
}

test_path_unit_no_after_relay_service() {
    local file_path="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.path"
    # shellcheck disable=SC2251
    ! grep -q "^After=checkmk_relay.service" "$file_path"
    assertEquals "Path unit must not have After=checkmk_relay.service (causes ordering cycle)" 0 $?
}

test_path_unit_no_wants_relay_service() {
    local file_path="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.path"
    # shellcheck disable=SC2251
    ! grep -q "^Wants=checkmk_relay.service" "$file_path"
    assertEquals "Path unit must not have Wants=checkmk_relay.service" 0 $?
}

test_path_unit_path_modified() {
    local file_path="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.path"
    grep -q "^PathModified=${TRIGGER_FILE}" "$file_path"
    assertEquals "Path unit should monitor correct trigger file" 0 $?
}

test_path_unit_triggers_service() {
    local file_path="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.path"
    grep -q "^Unit=checkmk_relay-update-manager.service" "$file_path"
    assertEquals "Path unit should trigger update manager service" 0 $?
}

test_path_unit_no_make_directory() {
    local file_path="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.path"
    # shellcheck disable=SC2251
    ! grep -q "^MakeDirectory=yes" "$file_path"
    assertEquals "Path unit must not have MakeDirectory=yes (watched path is a file)" 0 $?
}

test_path_unit_wanted_by_multi_user_target() {
    local file_path="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.path"
    grep -q "^WantedBy=multi-user.target" "$file_path"
    assertEquals "Path unit should be wanted by multi-user.target" 0 $?
}

# === Service Unit Tests ===

test_service_unit_in_system_dir() {
    assertTrue "Service unit should be in system systemd dir" \
        "[ -f '${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.service' ]"
}

test_service_unit_has_unit_section() {
    local file_path="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.service"
    grep -q "^\[Unit\]" "$file_path"
    assertEquals "Service unit should have [Unit] section" 0 $?
}

test_service_unit_has_service_section() {
    local file_path="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.service"
    grep -q "^\[Service\]" "$file_path"
    assertEquals "Service unit should have [Service] section" 0 $?
}

test_service_unit_no_install_section() {
    local file_path="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.service"
    # The update-manager service is a oneshot triggered only by the path unit.
    # It must not have an [Install] section.
    # shellcheck disable=SC2251
    ! grep -q "^\[Install\]" "$file_path"
    assertEquals "Service unit must not have [Install] section (only triggered by path unit)" 0 $?
}

test_service_unit_description() {
    local file_path="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.service"
    grep -q "^Description=Checkmk Relay Update Manager" "$file_path"
    assertEquals "Service unit should have correct description" 0 $?
}

test_service_unit_type() {
    local file_path="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.service"
    grep -q "^Type=oneshot" "$file_path"
    assertEquals "Service unit should be type oneshot" 0 $?
}

test_service_unit_exec_start() {
    local file_path="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.service"
    grep -q "^ExecStart=${UPDATE_SCRIPT_PATH}" "$file_path"
    assertEquals "Service unit should execute update script" 0 $?
}

test_service_unit_timeout() {
    local file_path="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.service"
    grep -q "^TimeoutStartSec=600" "$file_path"
    assertEquals "Service unit should have 600s timeout" 0 $?
}

test_service_unit_standard_output() {
    local file_path="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.service"
    grep -q "^StandardOutput=journal" "$file_path"
    assertEquals "Service unit should output to journal" 0 $?
}

test_service_unit_standard_error() {
    local file_path="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.service"
    grep -q "^StandardError=journal" "$file_path"
    assertEquals "Service unit should send errors to journal" 0 $?
}

test_service_unit_syslog_identifier() {
    local file_path="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.service"
    grep -q "^SyslogIdentifier=cmk-relay-updater" "$file_path"
    assertEquals "Service unit should have correct syslog identifier" 0 $?
}

test_service_unit_no_wanted_by() {
    local file_path="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.service"
    # shellcheck disable=SC2251
    ! grep -q "^WantedBy=" "$file_path"
    assertEquals "Service unit must not have WantedBy= (no [Install] section)" 0 $?
}

# === Integration Tests ===

test_all_three_units_generated() {
    local container_file="${QUADLET_DIR}/checkmk_relay.container"
    local path_file="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.path"
    local service_file="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.service"

    assertTrue "Container unit should exist" "[ -f '$container_file' ]"
    assertTrue "Path unit should exist" "[ -f '$path_file' ]"
    assertTrue "Service unit should exist" "[ -f '$service_file' ]"
}

test_units_reference_consistent_paths() {
    local service_file="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.service"
    local path_file="${SYSTEMD_SYSTEM_DIR}/checkmk_relay-update-manager.path"
    local container_file="${QUADLET_DIR}/checkmk_relay.container"

    # Service should reference update script
    grep -q "${UPDATE_SCRIPT_PATH}" "$service_file"
    assertEquals "Service should reference update script path" 0 $?

    # Path should reference trigger file
    grep -q "${TRIGGER_FILE}" "$path_file"
    assertEquals "Path should reference trigger file" 0 $?

    # Container should reference both trigger file and local tag
    grep -q "${TRIGGER_FILE}" "$container_file"
    assertEquals "Container should reference trigger file" 0 $?
    grep -q "${LOCAL_TAG_NAME}" "$container_file"
    assertEquals "Container should reference local tag" 0 $?
}

# shellcheck disable=SC1090
source "$UNIT_SH_SHUNIT2"
