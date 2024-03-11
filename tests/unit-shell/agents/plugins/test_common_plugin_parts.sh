#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

PLUGIN_STEM="${UNIT_SH_AGENTS_DIR}/plugins/"

MARK_B="# BEGIN COMMON PLUGIN CODE"
MARK_E="# END COMMON PLUGIN CODE"

_get_marked_lines() {
    awk "/$MARK_B/{f=1;next}/$MARK_E/{f=0}f" "$1"
}

test_common_code_blocks() {

    PLUGIN_BASELINE=$(_get_marked_lines "${PLUGIN_STEM}/kaspersky_av")

    while read -r file; do
        COMMON_BLOCK="$(_get_marked_lines "$file")"
        DIFF="$(diff <(echo "$PLUGIN_BASELINE") <(echo "$COMMON_BLOCK"))"
        assertEquals "PLUGIN: $file" "" "$DIFF"
    done < <(grep -ls "$MARK_B" "${PLUGIN_STEM}"*)

}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
