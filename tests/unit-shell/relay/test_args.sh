#!/bin/bash
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

oneTimeSetUp() {
    MK_SOURCE_ONLY="true" source "${UNIT_SH_REPO_PATH}/omd/non-free/relay/install_relay.sh"
    config

    # Save original functions
    # shellcheck disable=SC2317
    _original_usage() { usage "$@"; }
    # shellcheck disable=SC2317
    _original_die() { die "$@"; }
}

setUp() {
    # Reset args variables before each test
    ARGS_RELAY_NAME=""
    ARGS_INITIAL_TAG_VERSION=""
    ARGS_TARGET_SERVER=""
    ARGS_TARGET_SITE_NAME=""
    ARGS_USER=""
    ARGS_PASSWORD=""

    # Mock functions that parse_args depends on
    # shellcheck disable=SC2317
    usage() {
        exit 0
    }

    # shellcheck disable=SC2317
    die() {
        echo "ERROR: $*" >&2
        exit 1
    }
}

tearDown() {
    # Restore original functions
    # shellcheck disable=SC2317
    usage() { _original_usage "$@"; }
    # shellcheck disable=SC2317
    die() { _original_die "$@"; }
}

# Test: All required arguments provided
test_parse_args_all_required_args() {
    parse_args --relay-name "test-relay" \
        --initial-tag-version "1.0.0" \
        --target-server "server.example.com" \
        --target-site-name "mysite" \
        --user "testuser"

    assertEquals "test-relay" "$ARGS_RELAY_NAME"
    assertEquals "1.0.0" "$ARGS_INITIAL_TAG_VERSION"
    assertEquals "server.example.com" "$ARGS_TARGET_SERVER"
    assertEquals "mysite" "$ARGS_TARGET_SITE_NAME"
    assertEquals "testuser" "$ARGS_USER"
}

# Test: Arguments in different order
test_parse_args_different_order() {
    parse_args --target-site-name "mysite" \
        --relay-name "test-relay" \
        --target-server "server.example.com" \
        --initial-tag-version "1.0.0" \
        --user "testuser"

    assertEquals "test-relay" "$ARGS_RELAY_NAME"
    assertEquals "1.0.0" "$ARGS_INITIAL_TAG_VERSION"
    assertEquals "server.example.com" "$ARGS_TARGET_SERVER"
    assertEquals "mysite" "$ARGS_TARGET_SITE_NAME"
    assertEquals "testuser" "$ARGS_USER"
}

# Test: Missing --relay-name
test_parse_args_missing_relay_name() {
    (parse_args --initial-tag-version "1.0.0" \
        --target-server "server.example.com" \
        --target-site-name "mysite" \
        --user "testuser" 2>/dev/null)

    assertEquals 1 $?
}

# Test: Missing --initial-tag-version
test_parse_args_missing_initial_tag_version() {
    (parse_args --relay-name "test-relay" \
        --target-server "server.example.com" \
        --target-site-name "mysite" \
        --user "testuser" 2>/dev/null)

    assertEquals 1 $?
}

# Test: Missing --target-server
test_parse_args_missing_target_server() {
    (parse_args --relay-name "test-relay" \
        --initial-tag-version "1.0.0" \
        --target-site-name "mysite" \
        --user "testuser" 2>/dev/null)

    assertEquals 1 $?
}

# Test: Missing --target-site-name
test_parse_args_missing_target_site_name() {
    (parse_args --relay-name "test-relay" \
        --initial-tag-version "1.0.0" \
        --target-server "server.example.com" \
        --user "testuser" 2>/dev/null)

    assertEquals 1 $?
}

# Test: Unknown option
test_parse_args_unknown_option() {
    (parse_args --relay-name "test-relay" \
        --initial-tag-version "1.0.0" \
        --target-server "server.example.com" \
        --target-site-name "mysite" \
        --user "testuser" \
        --unknown-option "value" 2>/dev/null)

    assertEquals 1 $?
}

# Test: Help option (short form)
test_parse_args_help_short() {
    (parse_args -h)
    assertEquals 0 $?
}

# Test: Help option (long form)
test_parse_args_help_long() {
    (parse_args --help)
    assertEquals 0 $?
}

# Test: Values with spaces
test_parse_args_values_with_spaces() {
    parse_args --relay-name "test relay with spaces" \
        --initial-tag-version "1.0.0" \
        --target-server "server.example.com" \
        --target-site-name "my site" \
        --user "test user"

    assertEquals "test relay with spaces" "$ARGS_RELAY_NAME"
    assertEquals "my site" "$ARGS_TARGET_SITE_NAME"
    assertEquals "test user" "$ARGS_USER"
}

# Test: Values with special characters
test_parse_args_special_characters() {
    parse_args --relay-name "test-relay_v2" \
        --initial-tag-version "2.3.0-p1" \
        --target-server "https://server.example.com:8080" \
        --target-site-name "site_123" \
        --user "admin@example.com"

    assertEquals "test-relay_v2" "$ARGS_RELAY_NAME"
    assertEquals "2.3.0-p1" "$ARGS_INITIAL_TAG_VERSION"
    assertEquals "https://server.example.com:8080" "$ARGS_TARGET_SERVER"
    assertEquals "site_123" "$ARGS_TARGET_SITE_NAME"
    assertEquals "admin@example.com" "$ARGS_USER"
}

# Test: Empty string values should fail
test_parse_args_empty_relay_name() {
    (parse_args --relay-name "" \
        --initial-tag-version "1.0.0" \
        --target-server "server.example.com" \
        --target-site-name "mysite" \
        --user "testuser" 2>/dev/null)

    assertEquals 1 $?
}

# Test: No arguments at all
test_parse_args_no_arguments() {
    (parse_args 2>/dev/null)
    assertEquals 1 $?
}

# Test: Missing --user
test_parse_args_missing_user() {
    (parse_args --relay-name "test-relay" \
        --initial-tag-version "1.0.0" \
        --target-server "server.example.com" \
        --target-site-name "mysite" \
        2>/dev/null)

    assertEquals 1 $?
}

# Test: Empty user should fail
test_parse_args_empty_user() {
    (parse_args --relay-name "test-relay" \
        --initial-tag-version "1.0.0" \
        --target-server "server.example.com" \
        --target-site-name "mysite" \
        --user "" \
        2>/dev/null)

    assertEquals 1 $?
}

# Test: Password from stdin
test_request_password_from_stdin_valid() {
    # Simulate stdin input (not a TTY) using input redirection
    request_password < <(printf '%s' "my_secure_password")
    assertEquals "my_secure_password" "$ARGS_PASSWORD"
}

# Test: Password from stdin with special characters
test_request_password_from_stdin_special_chars() {
    # Test password with special characters
    request_password < <(printf '%s' 'P@ssw0rd!#$%&*()_+-={}[]|:;<>,.?/')
    assertEquals 'P@ssw0rd!#$%&*()_+-={}[]|:;<>,.?/' "$ARGS_PASSWORD"
}

# Test: Empty password from stdin
test_request_password_from_stdin_empty() {
    # Empty stdin should be accepted - the service will validate and reject
    request_password < <(printf '')
    assertEquals "" "$ARGS_PASSWORD"
}

# Test: Password prompt with TTY
test_request_password_with_tty_prompt() {
    # Create a wrapper script that sources install_relay.sh and calls request_password
    cat >"${SHUNIT_TMPDIR}/test_wrapper.sh" <<'WRAPPER_EOF'
#!/bin/bash
MK_SOURCE_ONLY="true" source "${UNIT_SH_REPO_PATH}/omd/non-free/relay/install_relay.sh"
ARGS_USER="testuser"
request_password
printf '%s' "$ARGS_PASSWORD"
WRAPPER_EOF
    chmod +x "${SHUNIT_TMPDIR}/test_wrapper.sh"

    # Use script to simulate TTY and provide password via stdin
    result=$(echo 'mypassword' | script -q -c "UNIT_SH_REPO_PATH='${UNIT_SH_REPO_PATH}' bash ${SHUNIT_TMPDIR}/test_wrapper.sh" /dev/null 2>&1 | tr -d '\r' | tail -n 1)

    assertEquals "mypassword" "$result"
}

# shellcheck disable=SC1090
source "$UNIT_SH_SHUNIT2"
