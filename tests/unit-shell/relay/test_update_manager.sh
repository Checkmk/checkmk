#!/bin/bash
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Unit tests for Relay Update Manager Script
# shellcheck disable=SC2016  # Single quotes in mock commands are intentional

INSTALL_SCRIPT="${UNIT_SH_REPO_PATH}/omd/non-free/relay/install_relay.sh"

# Test-specific variables
UPDATE_MANAGER_SCRIPT=""
TEST_TRIGGER_FILE=""

# Expected values constants
readonly TEST_VERSION="2.3.0"
readonly EXPECTED_REGISTRY="docker.io"
readonly EXPECTED_IMAGE_NAME="checkmk/check-mk-relay"
readonly EXPECTED_FULL_IMAGE="${EXPECTED_REGISTRY}/${EXPECTED_IMAGE_NAME}:${TEST_VERSION}"
readonly EXPECTED_LOCAL_TAG="localhost/checkmk_relay:checkmk_sync"

oneTimeSetUp() {
    # Create a test directory structure
    TEST_HOME="${SHUNIT_TMPDIR}/test_home"
    mkdir -p "${TEST_HOME}"

    # Save original environment
    ORIGINAL_HOME="${HOME}"
}

setUp() {
    # Set up test environment
    export HOME="${TEST_HOME}"

    # Clean up test home directory (including hidden files)
    if [ -d "${TEST_HOME}" ]; then
        find "${TEST_HOME}" -mindepth 1 -delete 2>/dev/null || true
    fi

    # Create directory structure
    mkdir -p "${TEST_HOME}/.local/share/checkmk_relay"
    mkdir -p "${TEST_HOME}/.local/bin"

    # Set paths
    TEST_TRIGGER_FILE="${TEST_HOME}/.local/share/checkmk_relay/update-trigger.conf"
    UPDATE_MANAGER_SCRIPT="${SHUNIT_TMPDIR}/checkmk_relay-update-manager.sh"

    # Extract update manager script from install_relay.sh
    bash <<EXTRACT_EOF
set +euo pipefail                      # Disable strict mode to allow sourcing
export MK_SOURCE_ONLY=1                # Prevent main() from running
source "${INSTALL_SCRIPT}" || true     # Load functions (ignore exit error)
UPDATE_SCRIPT_PATH="${UPDATE_MANAGER_SCRIPT}"
write_update_script >/dev/null 2>&1
EXTRACT_EOF

    # Health check: Verify the update manager script was successfully extracted
    if [ ! -f "${UPDATE_MANAGER_SCRIPT}" ]; then
        echo "FATAL ERROR: Failed to extract update manager script from install_relay.sh" >&2
        echo "  Expected location: ${UPDATE_MANAGER_SCRIPT}" >&2
        echo "  Install script: ${INSTALL_SCRIPT}" >&2
        echo "  This indicates a problem with the script extraction process." >&2
        return 1
    fi

    if [ ! -s "${UPDATE_MANAGER_SCRIPT}" ]; then
        echo "FATAL ERROR: Update manager script was created but is empty" >&2
        echo "  Location: ${UPDATE_MANAGER_SCRIPT}" >&2
        echo "  This indicates the write_update_script function did not write content." >&2
        return 1
    fi

    # Create mock directory for commands
    MOCK_BIN_DIR="${SHUNIT_TMPDIR}/mock_bin"
    rm -rf "${MOCK_BIN_DIR}" 2>/dev/null || true
    mkdir -p "${MOCK_BIN_DIR}"
    export PATH="${MOCK_BIN_DIR}:${PATH}"
}

tearDown() {
    # Clean up mock commands
    if [ -d "${MOCK_BIN_DIR}" ]; then
        rm -rf "${MOCK_BIN_DIR}" 2>/dev/null || true
    fi

    # Clean up update manager script
    if [ -f "${UPDATE_MANAGER_SCRIPT}" ]; then
        rm -f "${UPDATE_MANAGER_SCRIPT}"
    fi
}

oneTimeTearDown() {
    # Final cleanup
    if [ -d "${TEST_HOME}" ]; then
        rm -rf "${TEST_HOME}" 2>/dev/null || true
    fi

    # Restore original environment
    export HOME="${ORIGINAL_HOME}"
}

# Helper function to create mock commands
# Usage: create_mock_command <command_name> <script_content>
create_mock_command() {
    local cmd_name="$1"
    local cmd_script="$2"
    local cmd_path="${MOCK_BIN_DIR}/${cmd_name}"

    cat >"${cmd_path}" <<EOF
#!/bin/bash
${cmd_script}
EOF
    chmod +x "${cmd_path}"
}

# Helper function to create successful mock commands for podman and systemctl
# These mocks simulate successful execution of pull, tag, and systemctl operations
create_successful_mocks() {
    # Mock podman with success
    create_mock_command "podman" '
if [ "$1" = "pull" ]; then
    echo "Pulling image $2..." >&2
    exit 0
elif [ "$1" = "tag" ]; then
    echo "Tagging $2 as $3" >&2
    exit 0
else
    exit 0
fi
'

    # Mock systemctl with success
    create_mock_command "systemctl" '
if [ "$1" = "--user" ] && [ "$2" = "start" ]; then
    echo "Started $3" >&2
    exit 0
fi
exit 0
'
}

#------------------------------------------------------------------------------
# UMS-UP-01: Positive scenario where dependencies exist correctly
#------------------------------------------------------------------------------

test_UMS_UP_01_script_executes_successfully_with_valid_trigger() {
    create_successful_mocks

    # Create trigger file with valid version
    echo "${TEST_VERSION}" >"${TEST_TRIGGER_FILE}"

    # Run update manager script
    local exit_code=0
    bash "${UPDATE_MANAGER_SCRIPT}" >/dev/null 2>&1 || exit_code=$?

    # Check that script exits with success code
    assertEquals "Script should exit with code 0 on success" 0 "${exit_code}"
}

test_UMS_UP_01_commands_executed_in_correct_order() {
    # Create a log file to track command execution
    local cmd_log="${SHUNIT_TMPDIR}/cmd_log.txt"
    : >"${cmd_log}"

    # Mock commands that log their execution order
    create_mock_command "podman" "
echo \"\$(date +%s%N) podman \$*\" >> '${cmd_log}'
exit 0
"

    create_mock_command "systemctl" "
echo \"\$(date +%s%N) systemctl \$*\" >> '${cmd_log}'
exit 0
"

    # Create trigger file
    echo "${TEST_VERSION}" >"${TEST_TRIGGER_FILE}"

    # Run update manager script
    bash "${UPDATE_MANAGER_SCRIPT}" >/dev/null 2>&1 || true

    # Verify commands were executed with correct arguments
    assertTrue "podman pull should be executed with correct image" \
        "grep -q \"podman pull ${EXPECTED_FULL_IMAGE}\" '${cmd_log}'"

    assertTrue "podman tag should be executed with correct arguments" \
        "grep -q \"podman tag ${EXPECTED_FULL_IMAGE} ${EXPECTED_LOCAL_TAG}\" '${cmd_log}'"

    assertTrue "systemctl start should be executed" \
        "grep -q 'systemctl --user start podman-auto-update.service' '${cmd_log}'"

    # Verify order: podman pull comes before podman tag
    local pull_line tag_line systemctl_line
    pull_line=$(grep 'podman pull' "${cmd_log}" 2>/dev/null | head -1 | cut -d' ' -f1)
    tag_line=$(grep 'podman tag' "${cmd_log}" 2>/dev/null | head -1 | cut -d' ' -f1)
    systemctl_line=$(grep 'systemctl' "${cmd_log}" 2>/dev/null | head -1 | cut -d' ' -f1)

    if [ -n "${pull_line}" ] && [ -n "${tag_line}" ]; then
        assertTrue "podman pull should come before podman tag" \
            "[ ${pull_line} -lt ${tag_line} ]"
    fi

    # Verify order: podman tag comes before systemctl start
    if [ -n "${tag_line}" ] && [ -n "${systemctl_line}" ]; then
        assertTrue "podman tag should come before systemctl start" \
            "[ ${tag_line} -lt ${systemctl_line} ]"
    fi
}

#------------------------------------------------------------------------------
# UMS-ER-01: Run the script without the triggering file in its place
#------------------------------------------------------------------------------

test_UMS_ER_01_missing_trigger_file_produces_error() {
    create_successful_mocks

    # Do NOT create trigger file

    # Run update manager script once, capturing stderr and exit code
    local exit_code=0 stderr_file
    stderr_file="${SHUNIT_TMPDIR}/stderr.txt"

    bash "${UPDATE_MANAGER_SCRIPT}" 2>"${stderr_file}" || exit_code=$?

    local stderr_output
    stderr_output=$(cat "${stderr_file}" 2>/dev/null)

    # Check that script exits with error code
    assertNotEquals "Script should exit with non-zero code when trigger file is missing" 0 "${exit_code}"

    # Check for comprehensive error message
    if [[ "${stderr_output}" =~ missing ]] && [[ "${stderr_output}" =~ update-trigger ]]; then
        : # Pattern found, test passes
    else
        fail "Error message should mention trigger file is missing and include file path. Got: ${stderr_output}"
    fi
}

#------------------------------------------------------------------------------
# UMS-ER-02: Set the triggering file to an empty value
#------------------------------------------------------------------------------

test_UMS_ER_02_empty_trigger_file_produces_error() {
    create_successful_mocks

    # Create empty trigger file
    : >"${TEST_TRIGGER_FILE}"

    # Run update manager script and capture output
    local output exit_code=0
    output=$(bash "${UPDATE_MANAGER_SCRIPT}" 2>&1) || exit_code=$?

    # Check that script exits with error code
    assertNotEquals "Script should exit with non-zero code when trigger file is empty" 0 "${exit_code}"

    # Check for comprehensive error message
    if [[ "${output}" =~ "Trigger file is empty" ]]; then
        : # Pattern found, test passes
    else
        fail "Error message should mention 'Trigger file is empty'. Got: ${output}"
    fi
}

test_UMS_ER_02_empty_trigger_file_does_not_call_podman() {
    # Create a log to verify podman is not called
    local cmd_log="${SHUNIT_TMPDIR}/podman_log.txt"
    : >"${cmd_log}"

    create_mock_command "podman" "
echo 'podman called' >> '${cmd_log}'
exit 0
"

    create_mock_command "systemctl" "exit 0"

    # Create empty trigger file
    : >"${TEST_TRIGGER_FILE}"

    # Run update manager script
    bash "${UPDATE_MANAGER_SCRIPT}" >/dev/null 2>&1 || true

    # Verify podman was NOT called
    assertFalse "podman should not be called when trigger file is empty" \
        "test -s '${cmd_log}'"
}

#------------------------------------------------------------------------------
# UMS-ER-03: Set up the podman pull operation to fail
#------------------------------------------------------------------------------

test_UMS_ER_03_podman_pull_failure_produces_error() {
    # Mock podman to fail on pull
    create_mock_command "podman" '
if [ "$1" = "pull" ]; then
    echo "Error: failed to pull image: connection refused" >&2
    exit 1
else
    exit 0
fi
'

    create_mock_command "systemctl" "exit 0"

    # Create trigger file
    echo "${TEST_VERSION}" >"${TEST_TRIGGER_FILE}"

    # Run update manager script
    local output exit_code=0
    output=$(bash "${UPDATE_MANAGER_SCRIPT}" 2>&1) || exit_code=$?

    # Check that script exits with error code
    assertNotEquals "Script should exit with non-zero code when podman pull fails" 0 "${exit_code}"

    # Check that podman error message is propagated (not failing silently)
    if [[ "${output}" =~ "failed to pull image" ]]; then
        : # Pattern found, test passes
    else
        fail "Error output should include podman error message. Got: ${output}"
    fi
}

test_UMS_ER_03_podman_pull_failure_stops_execution() {
    # Create log files
    local pull_log="${SHUNIT_TMPDIR}/pull_log.txt"
    local tag_log="${SHUNIT_TMPDIR}/tag_log.txt"
    : >"${pull_log}"
    : >"${tag_log}"

    # Mock podman to fail on pull
    create_mock_command "podman" "
if [ \"\$1\" = \"pull\" ]; then
    echo 'pull attempted' >> '${pull_log}'
    exit 1
elif [ \"\$1\" = \"tag\" ]; then
    echo 'tag attempted' >> '${tag_log}'
    exit 0
fi
"

    create_mock_command "systemctl" "exit 0"

    # Create trigger file
    echo "${TEST_VERSION}" >"${TEST_TRIGGER_FILE}"

    # Run update manager script
    bash "${UPDATE_MANAGER_SCRIPT}" >/dev/null 2>&1 || true

    # Verify pull was attempted
    assertTrue "podman pull should be attempted" \
        "test -s '${pull_log}'"

    # Verify tag was NOT attempted (execution stopped)
    assertFalse "podman tag should not be attempted after pull failure" \
        "test -s '${tag_log}'"
}

#------------------------------------------------------------------------------
# UMS-ER-04: Set up the podman tag operation to fail
#------------------------------------------------------------------------------

test_UMS_ER_04_podman_tag_failure_produces_error() {
    # Mock podman to fail on tag
    create_mock_command "podman" '
if [ "$1" = "tag" ]; then
    echo "Error: failed to tag image: invalid reference format" >&2
    exit 1
else
    exit 0
fi
'

    create_mock_command "systemctl" "exit 0"

    # Create trigger file
    echo "${TEST_VERSION}" >"${TEST_TRIGGER_FILE}"

    # Run update manager script
    local output exit_code=0
    output=$(bash "${UPDATE_MANAGER_SCRIPT}" 2>&1) || exit_code=$?

    # Check that script exits with error code
    assertNotEquals "Script should exit with non-zero code when podman tag fails" 0 "${exit_code}"

    # Check that podman error message is propagated (not failing silently)
    if [[ "${output}" =~ "failed to tag image" ]]; then
        : # Pattern found, test passes
    else
        fail "Error output should include podman error message. Got: ${output}"
    fi
}

test_UMS_ER_04_podman_tag_failure_stops_execution() {
    # Create log files
    local tag_log="${SHUNIT_TMPDIR}/tag_log.txt"
    local systemctl_log="${SHUNIT_TMPDIR}/systemctl_log.txt"
    : >"${tag_log}"
    : >"${systemctl_log}"

    # Mock podman to fail on tag
    create_mock_command "podman" "
if [ \"\$1\" = \"tag\" ]; then
    echo 'tag attempted' >> '${tag_log}'
    exit 1
else
    exit 0
fi
"

    create_mock_command "systemctl" "
echo 'systemctl called' >> '${systemctl_log}'
exit 0
"

    # Create trigger file
    echo "${TEST_VERSION}" >"${TEST_TRIGGER_FILE}"

    # Run update manager script
    bash "${UPDATE_MANAGER_SCRIPT}" >/dev/null 2>&1 || true

    # Verify tag was attempted
    assertTrue "podman tag should be attempted" \
        "test -s '${tag_log}'"

    # Verify systemctl was NOT called (execution stopped)
    assertFalse "systemctl should not be called after tag failure" \
        "test -s '${systemctl_log}'"
}

#------------------------------------------------------------------------------
# UMS-ER-05: Set the systemctl start podman-auto-update.service to fail
#------------------------------------------------------------------------------

test_UMS_ER_05_systemctl_failure_produces_error() {
    # Mock systemctl to fail
    create_mock_command "systemctl" '
if [ "$1" = "--user" ] && [ "$2" = "start" ]; then
    echo "Failed to start podman-auto-update.service: Unit not found" >&2
    exit 1
fi
exit 0
'

    create_mock_command "podman" "exit 0"

    # Create trigger file
    echo "${TEST_VERSION}" >"${TEST_TRIGGER_FILE}"

    # Run update manager script
    local output exit_code=0
    output=$(bash "${UPDATE_MANAGER_SCRIPT}" 2>&1) || exit_code=$?

    # Check that script exits with error code
    assertNotEquals "Script should exit with non-zero code when systemctl fails" 0 "${exit_code}"

    # Check that systemctl error message is propagated (not failing silently)
    if [[ "${output}" =~ "Failed to start" ]]; then
        : # Pattern found, test passes
    else
        fail "Error output should include systemctl error message. Got: ${output}"
    fi
}

test_UMS_ER_05_systemctl_failure_after_successful_podman() {
    # Create log files to verify execution order
    local podman_log="${SHUNIT_TMPDIR}/podman_log.txt"
    local systemctl_log="${SHUNIT_TMPDIR}/systemctl_log.txt"
    : >"${podman_log}"
    : >"${systemctl_log}"

    create_mock_command "podman" "
echo \"podman \$*\" >> '${podman_log}'
exit 0
"

    create_mock_command "systemctl" "
echo 'systemctl called' >> '${systemctl_log}'
exit 1
"

    # Create trigger file
    echo "${TEST_VERSION}" >"${TEST_TRIGGER_FILE}"

    # Run update manager script
    bash "${UPDATE_MANAGER_SCRIPT}" >/dev/null 2>&1 || true

    # Verify podman operations completed successfully
    assertTrue "podman pull should be executed before systemctl failure" \
        "grep -q 'podman pull' '${podman_log}'"

    assertTrue "podman tag should be executed before systemctl failure" \
        "grep -q 'podman tag' '${podman_log}'"

    # Verify systemctl was attempted
    assertTrue "systemctl should be attempted" \
        "test -s '${systemctl_log}'"
}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
