#!/bin/bash
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

MK_JOB_STEM="${UNIT_SH_AGENTS_DIR}/mk-job"

MARK_B="# BEGIN PLATFORM SPECIFIC CODE"
MARK_E="# END PLATFORM SPECIFIC CODE"

_get_marked_lines() {
    awk "/^$/ {p=1} /$MARK_B/{p=0} p {print \$0 } p==0 && /$MARK_E/ {p = 1}" "$1"
    # start printing on first empty line
    # until MARK_B found, stop printing
    # until MARK_E found, then resume printing
}

test_common_code_blocks() {
    LINUX_REFERENCE=$(_get_marked_lines "${MK_JOB_STEM}")

    while read -r agent_file; do
        COMMON_BLOCK="$(_get_marked_lines "$agent_file")"
        DIFF="$(diff <(echo "$LINUX_REFERENCE") <(echo "$COMMON_BLOCK"))"
        assertEquals "MK_JOB: $agent_file" "" "$DIFF"
    done < <(grep -l "$MARK_B" "${MK_JOB_STEM}."*)

}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
