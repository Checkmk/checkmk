#!/bin/bash
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

oneTimeSetUp() {
    MK_SOURCE_ONLY="true" source "${UNIT_SH_REPO_PATH}/omd/non-free/relay/install_relay.sh"

    # Create temporary directory for test files
    TEST_DIR=$(mktemp -d)
    export CONFIG_HOME="${TEST_DIR}/.config"
    export DATA_HOME="${TEST_DIR}/.local/share"
    export BIN_HOME="${TEST_DIR}/.local/bin"

    # Initialize config
    config

    # Create necessary directories
    mkdir -p "$QUADLET_DIR"
    mkdir -p "$SYSTEMD_USER_DIR"
    mkdir -p "$APP_DATA_DIR"
    mkdir -p "$BIN_HOME"

    # Create trigger file
    echo "1.0.0" >"$TRIGGER_FILE"

    # Mock info function to suppress output during tests
    info() { :; }

    # Generate the systemd files
    write_systemd_units
}

oneTimeTearDown() {
    # Clean up temporary directory
    [ -d "$TEST_DIR" ] && rm -rf "$TEST_DIR"
    return 0
}

# === Container Unit Tests ===

test_container_unit_file_exists() {
    local file_path="${QUADLET_DIR}/checkmk_relay.container"
    assertTrue "Container unit file should exist" "[ -f '$file_path' ]"
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

test_container_unit_network_host() {
    local file_path="${QUADLET_DIR}/checkmk_relay.container"
    # shellcheck disable=SC2251
    ! grep -q "^Network=host" "$file_path"
    assertEquals "Container unit should not define Network=host" 0 $?
}

test_container_unit_exec() {
    local file_path="${QUADLET_DIR}/checkmk_relay.container"
    grep -q "^Exec=sh -c 'cmk-relay daemon'" "$file_path"
    assertEquals "Container unit should execute cmk-relay daemon" 0 $?
}

test_container_unit_trigger_volume() {
    local file_path="${QUADLET_DIR}/checkmk_relay.container"
    grep -q "^Volume=${TRIGGER_FILE}:/opt/check-mk-relay/workdir/site-version.txt:rw" "$file_path"
    assertEquals "Container unit should mount trigger file volume" 0 $?
}

test_container_unit_relay_volume() {
    local file_path="${QUADLET_DIR}/checkmk_relay.container"
    grep -q "^Volume=relay:/opt/check-mk-relay/workdir:rw" "$file_path"
    assertEquals "Container unit should mount relay volume" 0 $?
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

test_container_unit_wanted_by() {
    local file_path="${QUADLET_DIR}/checkmk_relay.container"
    grep -q "^WantedBy=default.target" "$file_path"
    assertEquals "Container unit should be wanted by default.target" 0 $?
}

# === Path Unit Tests ===

test_path_unit_file_exists() {
    local file_path="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.path"
    assertTrue "Path unit file should exist" "[ -f '$file_path' ]"
}

test_path_unit_has_unit_section() {
    local file_path="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.path"
    grep -q "^\[Unit\]" "$file_path"
    assertEquals "Path unit should have [Unit] section" 0 $?
}

test_path_unit_has_path_section() {
    local file_path="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.path"
    grep -q "^\[Path\]" "$file_path"
    assertEquals "Path unit should have [Path] section" 0 $?
}

test_path_unit_has_install_section() {
    local file_path="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.path"
    grep -q "^\[Install\]" "$file_path"
    assertEquals "Path unit should have [Install] section" 0 $?
}

test_path_unit_description() {
    local file_path="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.path"
    grep -q "^Description=Monitor Checkmk Relay Version File" "$file_path"
    assertEquals "Path unit should have correct description" 0 $?
}

test_path_unit_binds_to() {
    local file_path="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.path"
    grep -q "^BindsTo=checkmk_relay.service" "$file_path"
    assertEquals "Path unit should bind to checkmk_relay.service" 0 $?
}

test_path_unit_path_modified() {
    local file_path="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.path"
    grep -q "^PathModified=${TRIGGER_FILE}" "$file_path"
    assertEquals "Path unit should monitor correct trigger file" 0 $?
}

test_path_unit_triggers_service() {
    local file_path="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.path"
    grep -q "^Unit=checkmk_relay-update-manager.service" "$file_path"
    assertEquals "Path unit should trigger update manager service" 0 $?
}

test_path_unit_make_directory() {
    local file_path="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.path"
    grep -q "^MakeDirectory=yes" "$file_path"
    assertEquals "Path unit should have MakeDirectory=yes" 0 $?
}

test_path_unit_wanted_by() {
    local file_path="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.path"
    grep -q "^WantedBy=default.target" "$file_path"
    assertEquals "Path unit should be wanted by default.target" 0 $?
}

# === Service Unit Tests ===

test_service_unit_file_exists() {
    local file_path="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.service"
    assertTrue "Service unit file should exist" "[ -f '$file_path' ]"
}

test_service_unit_has_unit_section() {
    local file_path="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.service"
    grep -q "^\[Unit\]" "$file_path"
    assertEquals "Service unit should have [Unit] section" 0 $?
}

test_service_unit_has_service_section() {
    local file_path="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.service"
    grep -q "^\[Service\]" "$file_path"
    assertEquals "Service unit should have [Service] section" 0 $?
}

test_service_unit_has_install_section() {
    local file_path="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.service"
    grep -q "^\[Install\]" "$file_path"
    assertEquals "Service unit should have [Install] section" 0 $?
}

test_service_unit_description() {
    local file_path="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.service"
    grep -q "^Description=Checkmk Relay Update Manager" "$file_path"
    assertEquals "Service unit should have correct description" 0 $?
}

test_service_unit_type() {
    local file_path="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.service"
    grep -q "^Type=oneshot" "$file_path"
    assertEquals "Service unit should be type oneshot" 0 $?
}

test_service_unit_exec_start() {
    local file_path="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.service"
    grep -q "^ExecStart=${UPDATE_SCRIPT_PATH}" "$file_path"
    assertEquals "Service unit should execute update script" 0 $?
}

test_service_unit_timeout() {
    local file_path="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.service"
    grep -q "^TimeoutStartSec=600" "$file_path"
    assertEquals "Service unit should have 600s timeout" 0 $?
}

test_service_unit_standard_output() {
    local file_path="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.service"
    grep -q "^StandardOutput=journal" "$file_path"
    assertEquals "Service unit should output to journal" 0 $?
}

test_service_unit_standard_error() {
    local file_path="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.service"
    grep -q "^StandardError=journal" "$file_path"
    assertEquals "Service unit should send errors to journal" 0 $?
}

test_service_unit_syslog_identifier() {
    local file_path="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.service"
    grep -q "^SyslogIdentifier=cmk-relay-updater" "$file_path"
    assertEquals "Service unit should have correct syslog identifier" 0 $?
}

test_service_unit_wanted_by() {
    local file_path="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.service"
    grep -q "^WantedBy=default.target" "$file_path"
    assertEquals "Service unit should be wanted by default.target" 0 $?
}

# === Integration Tests ===

test_all_three_units_generated() {
    local container_file="${QUADLET_DIR}/checkmk_relay.container"
    local path_file="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.path"
    local service_file="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.service"

    assertTrue "Container unit should exist" "[ -f '$container_file' ]"
    assertTrue "Path unit should exist" "[ -f '$path_file' ]"
    assertTrue "Service unit should exist" "[ -f '$service_file' ]"
}

test_units_reference_consistent_paths() {
    local service_file="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.service"
    local path_file="${SYSTEMD_USER_DIR}/checkmk_relay-update-manager.path"
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
