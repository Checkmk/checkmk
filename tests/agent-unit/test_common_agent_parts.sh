#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


AGENT_LINUX="${UNIT_SH_AGENTS_DIR}/check_mk_agent.linux"

MARK_B="# BEGIN COMMON AGENT CODE"
MARK_E="# END COMMON AGENT CODE"

_get_marked_lines() {
    awk "/$MARK_B/{f=1;next}/$MARK_E/{f=0}f" "$1"
}

test_common_code_blocks () {

    LINUX_REFERENCE=$(_get_marked_lines "$AGENT_LINUX")

    while read -r agent_file; do
        COMMON_BLOCK="$(_get_marked_lines "$agent_file")"
        DIFF="$(diff <(echo "$LINUX_REFERENCE") <(echo "$COMMON_BLOCK"))"
        assertEquals "AGENT: $agent_file" "" "$DIFF"
    done < <(grep -l "$MARK_B" "${UNIT_SH_AGENTS_DIR}/check_mk_agent."*)

}


# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
