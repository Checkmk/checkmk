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

    # System mode requires root — mock as root by default
    # shellcheck disable=SC2317
    get_euid() { echo 0; }
    export -f get_euid

    # Point OS_RELEASE_FILE to a writable fake file seeded with the real OS
    # so existing tests using main() continue to work on supported distros
    OS_RELEASE_FILE="${TEST_DIR}/os-release"
    export OS_RELEASE_FILE
    if [[ -f /etc/os-release ]]; then
        cp /etc/os-release "$OS_RELEASE_FILE"
    fi
}

tearDown() {
    # Clean up temporary directory
    if [ -n "${TEST_DIR:-}" ] && [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
}

# Helper function to setup mocks for testing missing commands
setup_missing_command() {
    local missing_command="$1"
    export MISSING_COMMAND="$missing_command"

    # Mock command to simulate missing specified command
    # shellcheck disable=SC2317
    command() {
        if [[ "$1" == "-v" && "$2" == "$MISSING_COMMAND" ]]; then
            return 1 # specified command not found
        elif [[ "$1" == "-v" ]]; then
            return 0 # other commands are found
        else
            builtin command "$@"
        fi
    }
    export -f command
}

# Test: systemctl command is missing
# If systemctl is not found, main should fail with appropriate error message
test_missing_systemd() {
    setup_missing_command "systemctl"
    printf 'ID="ubuntu"\nVERSION_ID="24.04"\n' >"$OS_RELEASE_FILE"
    # shellcheck disable=SC2317
    uname() { echo "x86_64"; }
    export -f uname

    # Run main in a subshell to capture output and exit code
    set +e
    output=$(
        set -euo pipefail
        main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "server.example.com" \
            --target-site-name "mysite" \
            --token "testtoken" 2>&1
    )
    local exit_code=$?
    set -e

    # Assert that main exited with error
    assertNotEquals "main should exit with error" 0 "$exit_code"

    # Assert that the error message contains the expected text
    echo "$output" | grep -q "Systemd (systemctl) is not found."
    assertTrue "Error message should mention systemctl not found" $?
}

# Test: podman command is missing
# If podman is not found, main should fail with appropriate error message
test_missing_podman() {
    setup_missing_command "podman"
    printf 'ID="ubuntu"\nVERSION_ID="24.04"\n' >"$OS_RELEASE_FILE"
    # shellcheck disable=SC2317
    uname() { echo "x86_64"; }
    export -f uname

    # Run main in a subshell to capture output and exit code
    set +e
    output=$(
        set -euo pipefail
        main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "server.example.com" \
            --target-site-name "mysite" \
            --token "testtoken" 2>&1
    )
    local exit_code=$?
    set -e

    # Assert that main exited with error
    assertNotEquals "main should exit with error" 0 "$exit_code"

    # Assert that the error message contains the expected text
    echo "$output" | grep -q "Podman is not installed."
    assertTrue "Error message should mention podman not installed" $?
}

# Test: script runs as non-root
# System mode requires root; if run as a regular user it should fail
test_runs_as_non_root() {
    # Mock get_euid to return 1000 (non-root)
    # shellcheck disable=SC2317
    get_euid() { echo 1000; }
    export -f get_euid

    # Run main in a subshell to capture output and exit code
    set +e
    output=$(
        set -euo pipefail
        main --relay-name "test-relay" \
            --initial-tag-version "1.0.0" \
            --target-server "server.example.com" \
            --target-site-name "mysite" \
            --token "testtoken" 2>&1
    )
    local exit_code=$?
    set -e

    # Assert that main exited with error
    assertNotEquals "main should exit with error" 0 "$exit_code"

    # Assert that the error message contains the expected text
    echo "$output" | grep -q "This script must run as root."
    assertTrue "Error message should mention running as root required" $?
}

# Test: wrong architecture
# check_arch_x86_64 should fail when not running on x86_64
test_check_arch_x86_64_wrong_arch() {
    # shellcheck disable=SC2317
    uname() { echo "aarch64"; }
    export -f uname

    set +e
    output=$(check_arch_x86_64 2>&1)
    local exit_code=$?
    set -e

    assertNotEquals "should fail for non-x86_64 architecture" 0 "$exit_code"
    echo "$output" | grep -q "Unsupported architecture"
    assertTrue "Error message should mention unsupported architecture" $?
}

# Test: correct architecture
# check_arch_x86_64 should succeed when running on x86_64
test_check_arch_x86_64_correct_arch() {
    # shellcheck disable=SC2317
    uname() { echo "x86_64"; }
    export -f uname

    set +e
    output=$(check_arch_x86_64 2>&1)
    local exit_code=$?
    set -e

    assertEquals "should succeed for x86_64 architecture" 0 "$exit_code"
}

# Test: supported OS (exact match)
# warn_if_os_unsupported should succeed silently when OS matches a SUPPORTED_OS entry
test_warn_if_os_unsupported_supported_os() {
    printf 'ID="ubuntu"\nVERSION_ID="24.04"\n' >"$OS_RELEASE_FILE"
    SUPPORTED_OS=("ubuntu:24.04")

    set +e
    output=$(warn_if_os_unsupported 2>&1)
    local exit_code=$?
    set -e

    assertEquals "should succeed for exact OS match" 0 "$exit_code"
}

# Test: unsupported OS — default mock declines, so installation aborts
# warn_if_os_unsupported should warn and then abort (via _confirm_or_die) for unknown OS
test_warn_if_os_unsupported_unsupported_os_aborts() {
    printf 'ID="someos"\nVERSION_ID="99.99"\n' >"$OS_RELEASE_FILE"
    SUPPORTED_OS=("ubuntu:24.04" "rhel:9" "rhel:10")

    set +e
    output=$(warn_if_os_unsupported 2>&1)
    local exit_code=$?
    set -e

    assertNotEquals "should fail for unsupported OS when user declines" 0 "$exit_code"
    echo "$output" | grep -q "Unsupported OS"
    assertTrue "Output should mention unsupported OS" $?
}

# Test: unsupported OS — user confirms, installation continues
# warn_if_os_unsupported should return 0 when _confirm_or_die is overridden to accept
test_warn_if_os_unsupported_user_confirms_continues() {
    printf 'ID="someos"\nVERSION_ID="99.99"\n' >"$OS_RELEASE_FILE"
    SUPPORTED_OS=("ubuntu:24.04")
    # shellcheck disable=SC2317
    _confirm_or_die() { return 0; }
    export -f _confirm_or_die

    set +e
    output=$(warn_if_os_unsupported 2>&1)
    local exit_code=$?
    set -e

    assertEquals "should succeed when user confirms continuation" 0 "$exit_code"
}

# Test: RHEL with patch version
# warn_if_os_unsupported should succeed when RHEL reports a patch version (e.g. 9.7)
# because SUPPORTED_OS only lists the major version (e.g. rhel:9)
test_warn_if_os_unsupported_rhel_patch_version() {
    printf 'ID="rhel"\nVERSION_ID="9.7"\n' >"$OS_RELEASE_FILE"
    SUPPORTED_OS=("ubuntu:24.04" "rhel:9" "rhel:10")

    set +e
    output=$(warn_if_os_unsupported 2>&1)
    local exit_code=$?
    set -e

    assertEquals "rhel:9.7 should match supported entry rhel:9" 0 "$exit_code"
}

# Test: RHEL-like distros require explicit support
# AlmaLinux (ID=almalinux, ID_LIKE=rhel) must NOT be accepted just because
# it is RHEL-compatible — only distros with an explicit SUPPORTED_OS entry pass.
test_warn_if_os_unsupported_rhel_like_requires_explicit_support() {
    printf 'ID="almalinux"\nID_LIKE="rhel centos fedora"\nVERSION_ID="9.7"\n' >"$OS_RELEASE_FILE"
    SUPPORTED_OS=("ubuntu:24.04" "rhel:9" "rhel:10")

    set +e
    output=$(warn_if_os_unsupported 2>&1)
    local exit_code=$?
    set -e

    assertNotEquals "almalinux should be rejected without an explicit SUPPORTED_OS entry" 0 "$exit_code"
    echo "$output" | grep -q "Unsupported OS"
    assertTrue "Output should mention unsupported OS" $?
}

# Test: minimum patch level — patch at exactly the minimum is accepted
test_warn_if_os_unsupported_minimum_patch_level_exact() {
    printf 'ID="rhel"\nVERSION_ID="8.6"\n' >"$OS_RELEASE_FILE"
    SUPPORTED_OS=("rhel:8.6+")

    set +e
    output=$(warn_if_os_unsupported 2>&1)
    local exit_code=$?
    set -e

    assertEquals "rhel:8.6 should match minimum patch spec rhel:8.6" 0 "$exit_code"
}

# Test: minimum patch level — patch above minimum is accepted
test_warn_if_os_unsupported_minimum_patch_level_above() {
    printf 'ID="rhel"\nVERSION_ID="8.9"\n' >"$OS_RELEASE_FILE"
    SUPPORTED_OS=("rhel:8.6+")

    set +e
    output=$(warn_if_os_unsupported 2>&1)
    local exit_code=$?
    set -e

    assertEquals "rhel:8.9 should match minimum patch spec rhel:8.6" 0 "$exit_code"
}

# Test: minimum patch level — patch below minimum is rejected
test_warn_if_os_unsupported_minimum_patch_level_below() {
    printf 'ID="rhel"\nVERSION_ID="8.5"\n' >"$OS_RELEASE_FILE"
    SUPPORTED_OS=("rhel:8.6+")

    set +e
    output=$(warn_if_os_unsupported 2>&1)
    local exit_code=$?
    set -e

    assertNotEquals "rhel:8.5 should be rejected by minimum patch spec rhel:8.6" 0 "$exit_code"
    echo "$output" | grep -q "Unsupported OS"
    assertTrue "Output should mention unsupported OS" $?
}

# Test: minimum patch level — different major is rejected (+ locks to same major)
test_warn_if_os_unsupported_minimum_patch_level_wrong_major() {
    printf 'ID="rhel"\nVERSION_ID="9.0"\n' >"$OS_RELEASE_FILE"
    SUPPORTED_OS=("rhel:8.6+")

    set +e
    output=$(warn_if_os_unsupported 2>&1)
    local exit_code=$?
    set -e

    assertNotEquals "rhel:9.0 should not match rhel:8.6+ (major lock)" 0 "$exit_code"
    echo "$output" | grep -q "Unsupported OS"
    assertTrue "Output should mention unsupported OS" $?
}

# Test: missing os-release file — aborts by default (user declines via mock)
# warn_if_os_unsupported should prompt via _confirm_or_die when OS cannot be determined
test_warn_if_os_unsupported_no_os_release_aborts() {
    export OS_RELEASE_FILE="${TEST_DIR}/nonexistent-os-release"
    SUPPORTED_OS=("ubuntu:24.04" "rhel:9" "rhel:10")

    set +e
    output=$(warn_if_os_unsupported 2>&1)
    local exit_code=$?
    set -e

    assertNotEquals "should fail when os-release file is missing and user declines" 0 "$exit_code"
    echo "$output" | grep -q "Could not determine OS"
    assertTrue "Output should mention could not determine OS" $?
}

# Test: missing os-release file — user confirms, installation continues
test_warn_if_os_unsupported_no_os_release_user_confirms_continues() {
    export OS_RELEASE_FILE="${TEST_DIR}/nonexistent-os-release"
    SUPPORTED_OS=("ubuntu:24.04" "rhel:9" "rhel:10")
    # shellcheck disable=SC2317
    _confirm_or_die() { return 0; }
    export -f _confirm_or_die

    set +e
    output=$(warn_if_os_unsupported 2>&1)
    local exit_code=$?
    set -e

    assertEquals "should succeed when user confirms despite missing os-release" 0 "$exit_code"
}

# Test: podman --version output is unparseable (empty version field)
# check_podman_version should fail with a clear message, not a confusing "too old" error
test_check_podman_version_unparseable_output() {
    # shellcheck disable=SC2317
    _get_podman_version() { echo ""; }
    export -f _get_podman_version

    set +e
    output=$(check_podman_version 2>&1)
    local exit_code=$?
    set -e

    assertNotEquals "should fail when version cannot be parsed" 0 "$exit_code"
    echo "$output" | grep -q "Could not parse Podman version"
    assertTrue "Error message should mention unparseable version" $?
}

# Test: podman version too old
# check_podman_version should fail when installed podman is below minimum required
test_check_podman_version_too_old() {
    # shellcheck disable=SC2317
    _get_podman_version() { echo "4.3.9"; }
    export -f _get_podman_version

    set +e
    output=$(check_podman_version 2>&1)
    local exit_code=$?
    set -e

    assertNotEquals "should fail for podman version below 4.4" 0 "$exit_code"
    echo "$output" | grep -q "too old"
    assertTrue "Error message should mention version too old" $?
}

# Test: podman version at exact minimum
# check_podman_version should succeed when installed podman matches minimum version
test_check_podman_version_at_minimum() {
    # shellcheck disable=SC2317
    _get_podman_version() { echo "4.4.0"; }
    export -f _get_podman_version

    set +e
    output=$(check_podman_version 2>&1)
    local exit_code=$?
    set -e

    assertEquals "should succeed for podman version 4.4.0" 0 "$exit_code"
}

# Test: podman version above minimum
# check_podman_version should succeed when installed podman exceeds minimum version
test_check_podman_version_sufficient() {
    # shellcheck disable=SC2317
    _get_podman_version() { echo "5.2.1"; }
    export -f _get_podman_version

    set +e
    output=$(check_podman_version 2>&1)
    local exit_code=$?
    set -e

    assertEquals "should succeed for podman version above minimum" 0 "$exit_code"
}

# Test: Ubuntu exact match — a different release is rejected
# ubuntu:24.04 is an exact spec; ubuntu 22.04 must not match
test_warn_if_os_unsupported_ubuntu_different_version_rejected() {
    printf 'ID="ubuntu"\nVERSION_ID="22.04"\n' >"$OS_RELEASE_FILE"
    SUPPORTED_OS=("ubuntu:24.04")

    set +e
    output=$(warn_if_os_unsupported 2>&1)
    local exit_code=$?
    set -e

    assertNotEquals "ubuntu 22.04 should be rejected by exact spec ubuntu:24.04" 0 "$exit_code"
    echo "$output" | grep -q "Unsupported OS"
    assertTrue "Output should mention unsupported OS" $?
}

# Test: Ubuntu exact match — a newer minor release is rejected
# ubuntu:24.04 is exact; ubuntu 24.10 (interim release) must not match
test_warn_if_os_unsupported_ubuntu_newer_minor_rejected() {
    printf 'ID="ubuntu"\nVERSION_ID="24.10"\n' >"$OS_RELEASE_FILE"
    SUPPORTED_OS=("ubuntu:24.04")

    set +e
    output=$(warn_if_os_unsupported 2>&1)
    local exit_code=$?
    set -e

    assertNotEquals "ubuntu 24.10 should be rejected by exact spec ubuntu:24.04" 0 "$exit_code"
    echo "$output" | grep -q "Unsupported OS"
    assertTrue "Output should mention unsupported OS" $?
}

# Test: minimum patch with + — a different major is rejected
# rhel:9.7+ locks to the 9.x series; rhel 10.0 must not match
test_warn_if_os_unsupported_plus_spec_cross_major_rejected() {
    printf 'ID="rhel"\nVERSION_ID="10.0"\n' >"$OS_RELEASE_FILE"
    SUPPORTED_OS=("rhel:9.7+")

    set +e
    output=$(warn_if_os_unsupported 2>&1)
    local exit_code=$?
    set -e

    assertNotEquals "rhel 10.0 should not match rhel:9.7+ (major lock)" 0 "$exit_code"
    echo "$output" | grep -q "Unsupported OS"
    assertTrue "Output should mention unsupported OS" $?
}

# Test: warning message uses human-readable format, not raw internal tokens
test_warn_if_os_unsupported_message_human_readable() {
    printf 'ID="someos"\nVERSION_ID="1.0"\n' >"$OS_RELEASE_FILE"
    SUPPORTED_OS=("ubuntu:24.04" "rhel:9" "rhel:9.7+" "rhel:10")

    set +e
    output=$(warn_if_os_unsupported 2>&1)
    set -e

    # Must NOT show raw internal tokens
    # shellcheck disable=SC2251
    ! echo "$output" | grep -q "ubuntu:24.04"
    assertTrue "Output must not contain raw 'ubuntu:24.04'" $?

    # Must show human-readable phrases
    echo "$output" | grep -q "Ubuntu 24.04"
    assertTrue "Output should contain 'Ubuntu 24.04'" $?
    echo "$output" | grep -q "RHEL 9.x"
    assertTrue "Output should contain 'RHEL 9.x'" $?
    echo "$output" | grep -q "RHEL 9.7+"
    assertTrue "Output should contain 'RHEL 9.7+'" $?
    echo "$output" | grep -q "RHEL 10.x"
    assertTrue "Output should contain 'RHEL 10.x'" $?
}

# shellcheck disable=SC1090
source "$UNIT_SH_SHUNIT2"
