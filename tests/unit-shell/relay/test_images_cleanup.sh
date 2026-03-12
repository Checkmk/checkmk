#!/bin/bash
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Unit tests for Relay Update Manager - Image Cleanup
# shellcheck disable=SC2016  # Single quotes in mock commands are intentional

INSTALL_SCRIPT="${UNIT_SH_REPO_PATH}/omd/non-free/relay/install_relay.sh"

# Test-specific variables
UPDATE_MANAGER_SCRIPT=""
TEST_TRIGGER_FILE=""

readonly TEST_VERSION="2.3.0"

oneTimeSetUp() {
    TEST_HOME="${SHUNIT_TMPDIR}/test_home"
    mkdir -p "${TEST_HOME}"
    ORIGINAL_HOME="${HOME}"
}

setUp() {
    export HOME="${TEST_HOME}"

    if [ -d "${TEST_HOME}" ]; then
        find "${TEST_HOME}" -mindepth 1 -delete 2>/dev/null || true
    fi

    mkdir -p "${TEST_HOME}/opt/checkmk_relay"

    TEST_TRIGGER_FILE="${TEST_HOME}/opt/checkmk_relay/update-trigger.conf"
    export CHECKMK_RELAY_TRIGGER_FILE="${TEST_TRIGGER_FILE}"

    UPDATE_MANAGER_SCRIPT="${SHUNIT_TMPDIR}/checkmk_relay-update-manager.sh"

    # Extract update manager script from install_relay.sh
    bash <<EXTRACT_EOF
set +euo pipefail
export MK_SOURCE_ONLY=1
source "${INSTALL_SCRIPT}" || true
UPDATE_SCRIPT_PATH="${UPDATE_MANAGER_SCRIPT}"
write_update_script >/dev/null 2>&1
EXTRACT_EOF

    if [ ! -s "${UPDATE_MANAGER_SCRIPT}" ]; then
        echo "FATAL ERROR: Failed to extract update manager script" >&2
        return 1
    fi

    MOCK_BIN_DIR="${SHUNIT_TMPDIR}/mock_bin"
    rm -rf "${MOCK_BIN_DIR}" 2>/dev/null || true
    mkdir -p "${MOCK_BIN_DIR}"
    export PATH="${MOCK_BIN_DIR}:${PATH}"
}

tearDown() {
    if [ -d "${MOCK_BIN_DIR}" ]; then
        rm -rf "${MOCK_BIN_DIR}" 2>/dev/null || true
    fi
    if [ -f "${UPDATE_MANAGER_SCRIPT}" ]; then
        rm -f "${UPDATE_MANAGER_SCRIPT}"
    fi
}

oneTimeTearDown() {
    if [ -d "${TEST_HOME}" ]; then
        rm -rf "${TEST_HOME}" 2>/dev/null || true
    fi
    export HOME="${ORIGINAL_HOME}"
}

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

test_current_image_id_captured_before_pull() {
    local cmd_log="${SHUNIT_TMPDIR}/cmd_log.txt"
    : >"${cmd_log}"

    create_mock_command "podman" "
echo \"\$(date +%s%N) podman \$*\" >> '${cmd_log}'
if [ \"\$1\" = \"inspect\" ]; then
    echo 'sha256:aaaaold'
    exit 0
fi
exit 0
"
    create_mock_command "systemctl" "exit 0"

    echo "${TEST_VERSION}" >"${TEST_TRIGGER_FILE}"

    bash "${UPDATE_MANAGER_SCRIPT}" >/dev/null 2>&1 || true

    # Verify podman inspect is called on the local tag
    assertTrue "podman inspect should be called on local tag" \
        "grep -q 'podman inspect.*localhost/checkmk_relay:checkmk_sync' '${cmd_log}'"

    # Verify inspect happens before pull
    local inspect_line pull_line
    inspect_line=$(grep 'podman inspect' "${cmd_log}" | head -1 | cut -d' ' -f1)
    pull_line=$(grep 'podman pull' "${cmd_log}" | head -1 | cut -d' ' -f1)

    if [ -n "${inspect_line}" ] && [ -n "${pull_line}" ]; then
        assertTrue "podman inspect should come before podman pull" \
            "[ ${inspect_line} -lt ${pull_line} ]"
    else
        fail "Both podman inspect and podman pull should be called"
    fi
}

test_new_image_id_captured_after_tag() {
    local cmd_log="${SHUNIT_TMPDIR}/cmd_log.txt"
    : >"${cmd_log}"

    create_mock_command "podman" "
echo \"\$(date +%s%N) podman \$*\" >> '${cmd_log}'
if [ \"\$1\" = \"inspect\" ]; then
    echo 'sha256:aaaaold'
    exit 0
fi
exit 0
"
    create_mock_command "systemctl" "exit 0"

    echo "${TEST_VERSION}" >"${TEST_TRIGGER_FILE}"

    bash "${UPDATE_MANAGER_SCRIPT}" >/dev/null 2>&1 || true

    # There should be two podman inspect calls
    local inspect_count
    inspect_count=$(grep -c 'podman inspect' "${cmd_log}")
    assertEquals "podman inspect should be called twice" 2 "${inspect_count}"

    # Second inspect should come after tag
    local tag_line second_inspect_line
    tag_line=$(grep 'podman tag' "${cmd_log}" | head -1 | cut -d' ' -f1)
    second_inspect_line=$(grep 'podman inspect' "${cmd_log}" | tail -1 | cut -d' ' -f1)

    if [ -n "${tag_line}" ] && [ -n "${second_inspect_line}" ]; then
        assertTrue "second podman inspect should come after podman tag" \
            "[ ${tag_line} -lt ${second_inspect_line} ]"
    else
        fail "Both podman tag and second podman inspect should be called"
    fi
}

test_old_images_are_removed() {
    local cmd_log="${SHUNIT_TMPDIR}/cmd_log.txt"
    : >"${cmd_log}"

    # Mock podman: inspect returns different IDs for current vs new,
    # images lists three IDs (current, new, and one old)
    local call_count_file="${SHUNIT_TMPDIR}/inspect_count"
    echo "0" >"${call_count_file}"

    create_mock_command "podman" "
echo \"podman \$*\" >> '${cmd_log}'
if [ \"\$1\" = \"inspect\" ]; then
    count=\$(cat '${call_count_file}')
    count=\$((count + 1))
    echo \"\$count\" > '${call_count_file}'
    if [ \"\$count\" -eq 1 ]; then
        echo 'sha256:current111'
    else
        echo 'sha256:new222'
    fi
    exit 0
elif [ \"\$1\" = \"images\" ]; then
    echo 'sha256:current111'
    echo 'sha256:new222'
    echo 'sha256:old333'
    echo 'sha256:old444'
    exit 0
fi
exit 0
"
    create_mock_command "systemctl" "exit 0"

    echo "${TEST_VERSION}" >"${TEST_TRIGGER_FILE}"

    bash "${UPDATE_MANAGER_SCRIPT}" >/dev/null 2>&1 || true

    # Old images should be removed
    assertTrue "podman rmi should be called for old image" \
        "grep -q 'podman rmi sha256:old333' '${cmd_log}'"
    assertTrue "podman rmi should be called for old image" \
        "grep -q 'podman rmi sha256:old444' '${cmd_log}'"

    # Current and new images should NOT be removed
    assertFalse "podman rmi should not be called for current image" \
        "grep -q 'podman rmi sha256:current111' '${cmd_log}'"

    assertFalse "podman rmi should not be called for new image" \
        "grep -q 'podman rmi sha256:new222' '${cmd_log}'"
}

test_first_run_no_current_image() {
    local cmd_log="${SHUNIT_TMPDIR}/cmd_log.txt"
    : >"${cmd_log}"

    # First inspect fails (no existing image), second returns the new ID
    local call_count_file="${SHUNIT_TMPDIR}/inspect_count"
    echo "0" >"${call_count_file}"

    create_mock_command "podman" "
echo \"podman \$*\" >> '${cmd_log}'
if [ \"\$1\" = \"inspect\" ]; then
    count=\$(cat '${call_count_file}')
    count=\$((count + 1))
    echo \"\$count\" > '${call_count_file}'
    if [ \"\$count\" -eq 1 ]; then
        exit 1
    else
        echo 'sha256:new222'
    fi
    exit 0
elif [ \"\$1\" = \"images\" ]; then
    echo 'sha256:new222'
    exit 0
fi
exit 0
"
    create_mock_command "systemctl" "exit 0"

    echo "${TEST_VERSION}" >"${TEST_TRIGGER_FILE}"

    local exit_code=0
    bash "${UPDATE_MANAGER_SCRIPT}" >/dev/null 2>&1 || exit_code=$?

    assertEquals "Script should succeed on first run" 0 "${exit_code}"

    # New image should NOT be removed
    assertFalse "podman rmi should not be called for new image" \
        "grep -q 'podman rmi' '${cmd_log}'"
}

test_same_image_no_removal() {
    local cmd_log="${SHUNIT_TMPDIR}/cmd_log.txt"
    : >"${cmd_log}"

    # Both inspects return the same ID (no-op update)
    create_mock_command "podman" "
echo \"podman \$*\" >> '${cmd_log}'
if [ \"\$1\" = \"inspect\" ]; then
    echo 'sha256:same111'
    exit 0
elif [ \"\$1\" = \"images\" ]; then
    echo 'sha256:same111'
    exit 0
fi
exit 0
"
    create_mock_command "systemctl" "exit 0"

    echo "${TEST_VERSION}" >"${TEST_TRIGGER_FILE}"

    local exit_code=0
    bash "${UPDATE_MANAGER_SCRIPT}" >/dev/null 2>&1 || exit_code=$?

    assertEquals "Script should succeed on no-op update" 0 "${exit_code}"

    assertFalse "podman rmi should not be called when image unchanged" \
        "grep -q 'podman rmi' '${cmd_log}'"
}

test_no_cleanup_when_systemctl_fails() {
    local cmd_log="${SHUNIT_TMPDIR}/cmd_log.txt"
    : >"${cmd_log}"

    local call_count_file="${SHUNIT_TMPDIR}/inspect_count"
    echo "0" >"${call_count_file}"

    create_mock_command "podman" "
echo \"podman \$*\" >> '${cmd_log}'
if [ \"\$1\" = \"inspect\" ]; then
    count=\$(cat '${call_count_file}')
    count=\$((count + 1))
    echo \"\$count\" > '${call_count_file}'
    if [ \"\$count\" -eq 1 ]; then
        echo 'sha256:current111'
    else
        echo 'sha256:new222'
    fi
    exit 0
elif [ \"\$1\" = \"images\" ]; then
    echo 'sha256:current111'
    echo 'sha256:new222'
    echo 'sha256:old333'
    exit 0
fi
exit 0
"
    create_mock_command "systemctl" "exit 1"

    echo "${TEST_VERSION}" >"${TEST_TRIGGER_FILE}"

    bash "${UPDATE_MANAGER_SCRIPT}" >/dev/null 2>&1 || true

    assertFalse "podman rmi should not be called when systemctl fails" \
        "grep -q 'podman rmi' '${cmd_log}'"
}

test_no_old_images_no_removal() {
    local cmd_log="${SHUNIT_TMPDIR}/cmd_log.txt"
    : >"${cmd_log}"

    local call_count_file="${SHUNIT_TMPDIR}/inspect_count"
    echo "0" >"${call_count_file}"

    create_mock_command "podman" "
echo \"podman \$*\" >> '${cmd_log}'
if [ \"\$1\" = \"inspect\" ]; then
    count=\$(cat '${call_count_file}')
    count=\$((count + 1))
    echo \"\$count\" > '${call_count_file}'
    if [ \"\$count\" -eq 1 ]; then
        echo 'sha256:current111'
    else
        echo 'sha256:new222'
    fi
    exit 0
elif [ \"\$1\" = \"images\" ]; then
    echo 'sha256:current111'
    echo 'sha256:new222'
    exit 0
fi
exit 0
"
    create_mock_command "systemctl" "exit 0"

    echo "${TEST_VERSION}" >"${TEST_TRIGGER_FILE}"

    local exit_code=0
    bash "${UPDATE_MANAGER_SCRIPT}" >/dev/null 2>&1 || exit_code=$?

    assertEquals "Script should succeed when no old images exist" 0 "${exit_code}"

    assertFalse "podman rmi should not be called when there are no old images" \
        "grep -q 'podman rmi' '${cmd_log}'"
}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
