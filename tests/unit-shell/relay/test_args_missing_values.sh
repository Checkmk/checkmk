#!/bin/bash
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

oneTimeSetUp() {
    # shellcheck disable=SC1091
    MK_SOURCE_ONLY="true" source "${UNIT_SH_REPO_PATH}/omd/non-free/relay/install_relay.sh"
    config
}

setUp() {
    # Reset args variables before each test
    ARGS_RELAY_NAME=""
    ARGS_INITIAL_TAG_VERSION=""
    ARGS_TARGET_SERVER=""
    ARGS_TARGET_SITE_NAME=""
    ARGS_USER=""
    ARGS_PASSWORD=""
    ARGS_TOKEN=""

    # shellcheck disable=SC2317
    usage() { exit 0; }

    # shellcheck disable=SC2317
    die() {
        echo "ERROR: $*" >&2
        exit 1
    }
}

# --- --relay-name ---

test_parse_args_relay_name_missing_value() {
    (parse_args --initial-tag-version "1.0.0" \
        --target-server "s" --target-site-name "n" \
        --token "t" \
        --relay-name 2>/dev/null)
    assertEquals 1 $?
}

test_parse_args_relay_name_eats_next_flag() {
    (parse_args --relay-name --initial-tag-version "1.0.0" \
        --target-server "s" --target-site-name "n" \
        --token "t" 2>/dev/null)
    assertEquals 1 $?
}

# --- --initial-tag-version ---

test_parse_args_initial_tag_version_missing_value() {
    (parse_args --relay-name "r" \
        --target-server "s" --target-site-name "n" \
        --token "t" \
        --initial-tag-version 2>/dev/null)
    assertEquals 1 $?
}

test_parse_args_initial_tag_version_eats_next_flag() {
    (parse_args --relay-name "r" \
        --initial-tag-version --target-server "s" \
        --target-site-name "n" \
        --token "t" 2>/dev/null)
    assertEquals 1 $?
}

# --- --target-server ---

test_parse_args_target_server_missing_value() {
    (parse_args --relay-name "r" --initial-tag-version "1.0.0" \
        --target-site-name "n" \
        --token "t" \
        --target-server 2>/dev/null)
    assertEquals 1 $?
}

test_parse_args_target_server_eats_next_flag() {
    (parse_args --relay-name "r" --initial-tag-version "1.0.0" \
        --target-server --target-site-name "n" \
        --token "t" 2>/dev/null)
    assertEquals 1 $?
}

# --- --target-site-name ---

test_parse_args_target_site_name_missing_value() {
    (parse_args --relay-name "r" --initial-tag-version "1.0.0" \
        --target-server "s" \
        --token "t" \
        --target-site-name 2>/dev/null)
    assertEquals 1 $?
}

test_parse_args_target_site_name_eats_next_flag() {
    (parse_args --relay-name "r" --initial-tag-version "1.0.0" \
        --target-server "s" \
        --target-site-name --token "t" 2>/dev/null)
    assertEquals 1 $?
}

# --- --user ---

test_parse_args_user_missing_value() {
    (parse_args --relay-name "r" --initial-tag-version "1.0.0" \
        --target-server "s" --target-site-name "n" \
        --user 2>/dev/null)
    assertEquals 1 $?
}

test_parse_args_user_eats_next_flag() {
    (parse_args --relay-name "r" --initial-tag-version "1.0.0" \
        --user --target-server "s" \
        --target-site-name "n" 2>/dev/null)
    assertEquals 1 $?
}

# --- --token ---

test_parse_args_token_missing_value() {
    (parse_args --relay-name "r" --initial-tag-version "1.0.0" \
        --target-server "s" --target-site-name "n" \
        --token 2>/dev/null)
    assertEquals 1 $?
}

test_parse_args_token_eats_next_flag() {
    (parse_args --relay-name "r" --initial-tag-version "1.0.0" \
        --token --target-server "s" \
        --target-site-name "n" 2>/dev/null)
    assertEquals 1 $?
}

# --token eats --verbose (optional flag, so missing-arg validation won't catch it)
test_parse_args_token_eats_optional_flag() {
    (parse_args --relay-name "r" --initial-tag-version "1.0.0" \
        --target-server "s" --target-site-name "n" \
        --token --verbose 2>/dev/null)
    assertEquals 1 $?
}

# shellcheck disable=SC1090
source "$UNIT_SH_SHUNIT2"
