#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

oneTimeSetUp() {
    # shellcheck disable=SC1091
    MK_SOURCE_ONLY="true" source "${UNIT_SH_REPO_PATH}/non-free/packages/cmk-relay-engine/windows-installer/msi_version.sh"
}

assert_versions() {
    local raw="$1" expected_product="$2" expected_display="$3" out
    out="$(msi_version "$raw")"
    assertEquals "msi_version '$raw' failed" 0 $?
    assertEquals "$(printf '%s\n%s' "$expected_product" "$expected_display")" "$out"
}

assert_rejected() {
    (msi_version "$1" >/dev/null 2>&1)
    assertEquals "'$1' must be rejected" 1 $?
}

test_release() {
    assert_versions "2.6.0p1" "2.6.0" "2.6.0p1"
}

test_beta() {
    assert_versions "3.0.0b1" "3.0.0" "3.0.0b1"
}

test_plain() {
    assert_versions "2.6.0" "2.6.0" "2.6.0"
}

test_version_branch_daily() {
    assert_versions "2.6.0-2026.05.20" "2.6.0" "2.6.0-2026.05.20"
}

test_long_patch_is_kept() {
    assert_versions "2.6.123" "2.6.123" "2.6.123"
}

test_stray_quotes_and_whitespace() {
    assert_versions " '3.0.0'-2026.06.11 " "3.0.0" "3.0.0-2026.06.11"
}

test_date_only_is_rejected() {
    assert_rejected "2026.05.20"
}

test_unset_is_rejected() {
    assert_rejected "UNSET"
}

test_non_numeric_is_rejected() {
    assert_rejected "master"
}

test_two_components_are_rejected() {
    assert_rejected "2.6"
}

# shellcheck disable=SC1090
source "$UNIT_SH_SHUNIT2"
