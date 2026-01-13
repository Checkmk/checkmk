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
        --user "testuser" \
        --password "testpass"

    assertEquals "test-relay" "$ARGS_RELAY_NAME"
    assertEquals "1.0.0" "$ARGS_INITIAL_TAG_VERSION"
    assertEquals "server.example.com" "$ARGS_TARGET_SERVER"
    assertEquals "mysite" "$ARGS_TARGET_SITE_NAME"
    assertEquals "testuser" "$ARGS_USER"
    assertEquals "testpass" "$ARGS_PASSWORD"
}

# Test: Arguments in different order
test_parse_args_different_order() {
    parse_args --target-site-name "mysite" \
        --relay-name "test-relay" \
        --target-server "server.example.com" \
        --initial-tag-version "1.0.0" \
        --password "testpass" \
        --user "testuser"

    assertEquals "test-relay" "$ARGS_RELAY_NAME"
    assertEquals "1.0.0" "$ARGS_INITIAL_TAG_VERSION"
    assertEquals "server.example.com" "$ARGS_TARGET_SERVER"
    assertEquals "mysite" "$ARGS_TARGET_SITE_NAME"
    assertEquals "testuser" "$ARGS_USER"
    assertEquals "testpass" "$ARGS_PASSWORD"
}

# Test: Missing --relay-name
test_parse_args_missing_relay_name() {
    (parse_args --initial-tag-version "1.0.0" \
        --target-server "server.example.com" \
        --target-site-name "mysite" \
        --user "testuser" \
        --password "testpass" 2>/dev/null)

    assertEquals 1 $?
}

# Test: Missing --initial-tag-version
test_parse_args_missing_initial_tag_version() {
    (parse_args --relay-name "test-relay" \
        --target-server "server.example.com" \
        --target-site-name "mysite" \
        --user "testuser" \
        --password "testpass" 2>/dev/null)

    assertEquals 1 $?
}

# Test: Missing --target-server
test_parse_args_missing_target_server() {
    (parse_args --relay-name "test-relay" \
        --initial-tag-version "1.0.0" \
        --target-site-name "mysite" \
        --user "testuser" \
        --password "testpass" 2>/dev/null)

    assertEquals 1 $?
}

# Test: Missing --target-site-name
test_parse_args_missing_target_site_name() {
    (parse_args --relay-name "test-relay" \
        --initial-tag-version "1.0.0" \
        --target-server "server.example.com" \
        --user "testuser" \
        --password "testpass" 2>/dev/null)

    assertEquals 1 $?
}

# Test: Unknown option
test_parse_args_unknown_option() {
    (parse_args --relay-name "test-relay" \
        --initial-tag-version "1.0.0" \
        --target-server "server.example.com" \
        --target-site-name "mysite" \
        --user "testuser" \
        --password "testpass" \
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
        --user "test user" \
        --password "test pass"

    assertEquals "test relay with spaces" "$ARGS_RELAY_NAME"
    assertEquals "my site" "$ARGS_TARGET_SITE_NAME"
    assertEquals "test user" "$ARGS_USER"
    assertEquals "test pass" "$ARGS_PASSWORD"
}

# Test: Values with special characters
test_parse_args_special_characters() {
    parse_args --relay-name "test-relay_v2" \
        --initial-tag-version "2.3.0-p1" \
        --target-server "https://server.example.com:8080" \
        --target-site-name "site_123" \
        --user "admin@example.com" \
        --password "P@ssw0rd!#$"

    assertEquals "test-relay_v2" "$ARGS_RELAY_NAME"
    assertEquals "2.3.0-p1" "$ARGS_INITIAL_TAG_VERSION"
    assertEquals "https://server.example.com:8080" "$ARGS_TARGET_SERVER"
    assertEquals "site_123" "$ARGS_TARGET_SITE_NAME"
    assertEquals "admin@example.com" "$ARGS_USER"
    assertEquals "P@ssw0rd!#$" "$ARGS_PASSWORD"
}

# Test: Empty string values should fail
test_parse_args_empty_relay_name() {
    (parse_args --relay-name "" \
        --initial-tag-version "1.0.0" \
        --target-server "server.example.com" \
        --target-site-name "mysite" \
        --user "testuser" \
        --password "testpass" 2>/dev/null)

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
        --password "testpass" 2>/dev/null)

    assertEquals 1 $?
}

# Test: Missing --password
test_parse_args_missing_password() {
    (parse_args --relay-name "test-relay" \
        --initial-tag-version "1.0.0" \
        --target-server "server.example.com" \
        --target-site-name "mysite" \
        --user "testuser" 2>/dev/null)

    assertEquals 1 $?
}

# Test: Empty user should fail
test_parse_args_empty_user() {
    (parse_args --relay-name "test-relay" \
        --initial-tag-version "1.0.0" \
        --target-server "server.example.com" \
        --target-site-name "mysite" \
        --user "" \
        --password "testpass" 2>/dev/null)

    assertEquals 1 $?
}

# Test: Empty password should fail
test_parse_args_empty_password() {
    (parse_args --relay-name "test-relay" \
        --initial-tag-version "1.0.0" \
        --target-server "server.example.com" \
        --target-site-name "mysite" \
        --user "testuser" \
        --password "" 2>/dev/null)

    assertEquals 1 $?
}

# Test: User and password with special characters
test_parse_args_user_password_special_chars() {
    parse_args --relay-name "test-relay" \
        --initial-tag-version "1.0.0" \
        --target-server "server.example.com" \
        --target-site-name "mysite" \
        --user "user@domain.com" \
        --password "P@ss!w0rd#123"

    assertEquals "user@domain.com" "$ARGS_USER"
    assertEquals "P@ss!w0rd#123" "$ARGS_PASSWORD"
}

# shellcheck disable=SC1090
source "$UNIT_SH_SHUNIT2"
