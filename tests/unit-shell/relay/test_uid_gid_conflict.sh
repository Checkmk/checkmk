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

    TEST_DIR=$(mktemp -d)
    export CHECKMK_RELAY_DATA_DIR="${TEST_DIR}/opt/checkmk_relay"
    export CHECKMK_RELAY_BIN_DIR="${TEST_DIR}/usr/local/bin"
    export CHECKMK_RELAY_SYSTEMD_DIR="${TEST_DIR}/etc/systemd/system"
    export CHECKMK_RELAY_QUADLET_DIR="${TEST_DIR}/etc/containers/systemd"

    # shellcheck disable=SC2317
    get_euid() { echo 0; }
    export -f get_euid

    # Capture warn calls for assertion; use a plain variable instead of an array
    # so it is accessible even when exported across function boundaries.
    WARN_LOG=""
    # shellcheck disable=SC2317
    warn() { WARN_LOG="${WARN_LOG}|$*"; }
    export -f warn

    # Default: no UID/GID conflict on the host
    # shellcheck disable=SC2317
    getent() {
        if [[ "$1" == "ahosts" ]]; then
            builtin echo "192.168.1.1     STREAM $2"
            return 0
        fi
        return 1
    }
    export -f getent

    # Point LOGIN_DEFS_FILE to a nonexistent path so the login.defs check is a
    # no-op by default; individual tests create the file as needed.
    LOGIN_DEFS_FILE="${TEST_DIR}/login.defs"

    # Variables set by config() in production; initialize them here since
    # config() is not called when MK_SOURCE_ONLY=true.
    HOST_CONTAINER_UID=99000
    HOST_CONTAINER_GID=99000

    ARGS_FORCE=""
}

tearDown() {
    if [[ -n "${TEST_DIR:-}" && -d "$TEST_DIR" ]]; then
        rm -rf "$TEST_DIR"
    fi
}

# ---------------------------------------------------------------------------
# Helpers: override getent to simulate specific conflict scenarios
# ---------------------------------------------------------------------------
_mock_uid_conflict() {
    # shellcheck disable=SC2317
    getent() {
        if [[ "$1" == "ahosts" ]]; then
            builtin echo "192.168.1.1     STREAM $2"
            return 0
        fi
        if [[ "$1" == "passwd" && "$2" == "99000" ]]; then
            builtin echo "conflictuser:x:99000:99000:Conflict User:/home/conflictuser:/bin/bash"
            return 0
        fi
        return 1
    }
    export -f getent
}

_mock_gid_conflict() {
    # shellcheck disable=SC2317
    getent() {
        if [[ "$1" == "ahosts" ]]; then
            builtin echo "192.168.1.1     STREAM $2"
            return 0
        fi
        if [[ "$1" == "group" && "$2" == "99000" ]]; then
            builtin echo "conflictgroup:x:99000:"
            return 0
        fi
        return 1
    }
    export -f getent
}

_mock_both_conflicts() {
    # shellcheck disable=SC2317
    getent() {
        if [[ "$1" == "ahosts" ]]; then
            builtin echo "192.168.1.1     STREAM $2"
            return 0
        fi
        if [[ "$1" == "passwd" && "$2" == "99000" ]]; then
            builtin echo "conflictuser:x:99000:99000:Conflict User:/home/conflictuser:/bin/bash"
            return 0
        fi
        if [[ "$1" == "group" && "$2" == "99000" ]]; then
            builtin echo "conflictgroup:x:99000:"
            return 0
        fi
        return 1
    }
    export -f getent
}

# Write a login.defs file into TEST_DIR with the given SUB_UID_MIN and UID_MAX.
_write_login_defs() {
    local sub_uid_min="$1" uid_max="$2"
    # shellcheck disable=SC2119  # cat used with heredoc, not passing function args
    cat >"${TEST_DIR}/login.defs" <<EOF
# test login.defs
UID_MIN    1000
UID_MAX    ${uid_max}
SUB_UID_MIN    ${sub_uid_min}
SUB_UID_MAX    600100000
SUB_UID_COUNT  65536
EOF
}

# ---------------------------------------------------------------------------
# Test: no conflict → succeeds silently, no warnings
# ---------------------------------------------------------------------------
test_no_conflict_passes_silently() {
    check_uid_gid_conflict

    assertEquals "No warnings should be emitted when there is no conflict" \
        "" "$WARN_LOG"
}

# ---------------------------------------------------------------------------
# Test: UID 99000 in use → warning mentions the username
# ---------------------------------------------------------------------------
test_uid_conflict_warns_with_username() {
    _mock_uid_conflict
    ARGS_FORCE="true"

    check_uid_gid_conflict

    echo "$WARN_LOG" | grep -q "UID 99000.*conflictuser"
    assertTrue "Warning should mention UID 99000 and the conflicting username" $?
}

# ---------------------------------------------------------------------------
# Test: GID 99000 in use → warning mentions the group name
# ---------------------------------------------------------------------------
test_gid_conflict_warns_with_groupname() {
    _mock_gid_conflict
    ARGS_FORCE="true"

    check_uid_gid_conflict

    echo "$WARN_LOG" | grep -q "GID 99000.*conflictgroup"
    assertTrue "Warning should mention GID 99000 and the conflicting group name" $?
}

# ---------------------------------------------------------------------------
# Test: both UID and GID in use → both warnings present
# ---------------------------------------------------------------------------
test_both_conflicts_emit_uid_and_gid_warnings() {
    _mock_both_conflicts
    ARGS_FORCE="true"

    check_uid_gid_conflict

    echo "$WARN_LOG" | grep -q "UID 99000"
    assertTrue "UID warning should be present" $?

    echo "$WARN_LOG" | grep -q "GID 99000"
    assertTrue "GID warning should be present" $?
}

# ---------------------------------------------------------------------------
# Test: conflict + --force → no prompt, returns 0
# ---------------------------------------------------------------------------
test_conflict_with_force_skips_prompt() {
    _mock_uid_conflict
    ARGS_FORCE="true"

    set +e
    check_uid_gid_conflict
    local exit_code=$?
    set -e

    assertEquals "check_uid_gid_conflict should succeed with --force" 0 "$exit_code"
}

# ---------------------------------------------------------------------------
# login.defs range check tests
# ---------------------------------------------------------------------------

# No login.defs file → check is skipped, no warning
test_logindefs_missing_file_no_warning() {
    # LOGIN_DEFS_FILE points to nonexistent path (setUp default)
    check_uid_gid_conflict

    assertEquals "No warning when login.defs is absent" "" "$WARN_LOG"
}

# Only SUB_UID_MIN present (UID_MAX absent) → no warning, no crash
test_logindefs_only_sub_uid_min_present_no_warning() {
    # shellcheck disable=SC2119  # cat used with heredoc, not passing function args
    cat >"${TEST_DIR}/login.defs" <<'EOF'
SUB_UID_MIN    65536
EOF
    ARGS_FORCE="true"

    check_uid_gid_conflict

    assertEquals "No warning when UID_MAX is absent from login.defs" "" "$WARN_LOG"
}

# Only UID_MAX present (SUB_UID_MIN absent) → no warning, no crash
test_logindefs_only_uid_max_present_no_warning() {
    # shellcheck disable=SC2119  # cat used with heredoc, not passing function args
    cat >"${TEST_DIR}/login.defs" <<'EOF'
UID_MAX    100000
EOF
    ARGS_FORCE="true"

    check_uid_gid_conflict

    assertEquals "No warning when SUB_UID_MIN is absent from login.defs" "" "$WARN_LOG"
}

# SUB_UID_MIN >= HOST_CONTAINER_UID → no conflict (normal system defaults)
test_logindefs_sub_uid_min_above_host_uid_no_warning() {
    _write_login_defs 100000 60000 # SUB_UID_MIN=100000 > 99000, UID_MAX=60000 < 99000
    ARGS_FORCE="true"

    check_uid_gid_conflict

    assertEquals "No warning when SUB_UID_MIN is above the relay host UID" "" "$WARN_LOG"
}

# UID_MAX <= HOST_CONTAINER_UID → no conflict
test_logindefs_uid_max_below_host_uid_no_warning() {
    _write_login_defs 65536 60000 # SUB_UID_MIN=65536 < 99000 but UID_MAX=60000 < 99000
    ARGS_FORCE="true"

    check_uid_gid_conflict

    assertEquals "No warning when UID_MAX is below the relay host UID" "" "$WARN_LOG"
}

# SUB_UID_MIN < HOST_CONTAINER_UID AND UID_MAX > HOST_CONTAINER_UID → warning
test_logindefs_ambiguous_range_warns() {
    _write_login_defs 65536 100000 # SUB_UID_MIN=65536 < 99000 < UID_MAX=100000
    ARGS_FORCE="true"

    check_uid_gid_conflict

    echo "$WARN_LOG" | grep -q "may already be in use"
    assertTrue "Warning should explain the potential conflict" $?

    echo "$WARN_LOG" | grep -q "65536"
    assertTrue "Warning should include the SUB_UID_MIN value" $?

    echo "$WARN_LOG" | grep -q "100000"
    assertTrue "Warning should include the UID_MAX value" $?
}

# login.defs conflict + --force → warning shown but no prompt (returns 0)
test_logindefs_conflict_with_force_skips_prompt() {
    _write_login_defs 65536 100000
    ARGS_FORCE="true"

    set +e
    check_uid_gid_conflict
    local exit_code=$?
    set -e

    assertEquals "Should succeed with --force even when login.defs warns" 0 "$exit_code"
    echo "$WARN_LOG" | grep -q "may already be in use"
    assertTrue "Warning should still be emitted when --force is set" $?
}

# ---------------------------------------------------------------------------
# Tests for interactive y/n prompt (require a real tty via `script`)
# ---------------------------------------------------------------------------

# Run check_uid_gid_conflict (with a UID conflict) in a wrapper script that
# provides a real /dev/tty via `script`. The wrapper prints "RESULT:0" on
# success and "RESULT:1" on failure, so the caller can assert the outcome
# without relying on `script`'s exit-code propagation (which is unreliable
# across util-linux versions).
_run_conflict_wrapper_with_input() {
    local answer_input="$1"
    local wrapper="${SHUNIT_TMPDIR}/test_uid_conflict_wrapper.sh"

    # shellcheck disable=SC2119  # cat used with heredoc, not passing function args
    cat >"$wrapper" <<'WRAPPER_EOF'
#!/bin/bash
set +euo pipefail
# install_relay.sh has `set -euo pipefail` at its top level and its last
# statement `[ -z "${MK_SOURCE_ONLY:-}" ]` returns 1 when MK_SOURCE_ONLY is
# set.  Using `|| true` prevents that non-zero exit from terminating this
# wrapper when strict mode re-activates mid-source.
MK_SOURCE_ONLY="true" source "${UNIT_SH_REPO_PATH}/omd/non-free/relay/install_relay.sh" || true
set +euo pipefail

# shellcheck disable=SC2317
getent() {
    if [[ "$1" == "passwd" && "$2" == "99000" ]]; then
        builtin echo "conflictuser:x:99000:99000:Conflict User:/home/c:/bin/bash"
        return 0
    fi
    return 1
}
export -f getent

# shellcheck disable=SC2317
warn() { :; }
export -f warn

HOST_CONTAINER_UID=99000
HOST_CONTAINER_GID=99000
LOGIN_DEFS_FILE="/nonexistent/login.defs"
ARGS_FORCE=""
# Run in a subshell so that die()/exit 1 does not kill this wrapper script;
# the wrapper always reaches the echo and prints a deterministic result marker.
(check_uid_gid_conflict)
builtin echo "RESULT:$?"
WRAPPER_EOF

    chmod +x "$wrapper"
    builtin echo "$answer_input" | script -q -c \
        "UNIT_SH_REPO_PATH='${UNIT_SH_REPO_PATH}' bash ${wrapper}" \
        /dev/null 2>&1 | tr -d '\r'
}

# Test: conflict + user answers 'y' → RESULT:0
test_conflict_user_confirms_yes() {
    set +e
    local output
    output=$(_run_conflict_wrapper_with_input "y")
    set -e

    echo "$output" | grep -q "RESULT:0"
    assertTrue "check_uid_gid_conflict should succeed when user answers y" $?
}

# Test: conflict + user answers 'n' → RESULT:1 (die was called)
test_conflict_user_declines_aborts() {
    set +e
    local output
    output=$(_run_conflict_wrapper_with_input "n")
    set -e

    echo "$output" | grep -q "RESULT:1"
    assertTrue "check_uid_gid_conflict should fail when user answers n" $?
}

# Test: conflict + empty answer (just Enter) → RESULT:1 (default is N)
test_conflict_empty_answer_aborts() {
    set +e
    local output
    output=$(_run_conflict_wrapper_with_input "")
    set -e

    echo "$output" | grep -q "RESULT:1"
    assertTrue "check_uid_gid_conflict should fail on empty/Enter answer" $?
}

# shellcheck disable=SC1090
source "$UNIT_SH_SHUNIT2"
