#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

AGENT_LINUX="${UNIT_SH_AGENTS_DIR}/check_mk_agent.linux"

# shellcheck source=agents/check_mk_agent.linux
MK_SOURCE_AGENT="true" source "$AGENT_LINUX"

test_set_up_path_already_in_path() {
    assertEquals "/foo:/usr/local/bin:/bar" "$(set_up_path "/foo:/usr/local/bin:/bar")"
}

test_set_up_path_extended() {
    assertEquals "/foo:/bar:/usr/local/bin" "$(set_up_path "/foo:/bar")"
}

test_set_up_path_extended_optional_cmk_bin() {
    export MK_BIN="/opt/cmk/bin"
    assertEquals "/usr/local/bin:/opt/cmk/bin" "$(set_up_path "/usr/local/bin")"
}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
