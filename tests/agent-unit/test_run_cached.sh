#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


AGENT_LINUX="${UNIT_SH_AGENTS_DIR}/check_mk_agent.linux"

# shellcheck source=../../agents/check_mk_agent.linux
MK_SOURCE_AGENT="true" source "$AGENT_LINUX"

oneTimeSetUp() {

    export MK_VARDIR="${SHUNIT_TMPDIR}"
    mkdir -p "$MK_VARDIR/cache/"

    PLUG_CACHE="$MK_VARDIR/cache/plugins_my_plugin.cache"
    LOCA_CACHE="$MK_VARDIR/cache/local_my_local_check.cache"
    MRPE_CACHE="$MK_VARDIR/cache/mrpe_mrpetest.cache"

    # create some caches. Note that mrpe includes a section header
    echo 'P "This is local output"' >> "$LOCA_CACHE"
    echo -e "<<<mrpe>>>\n(my_check) Description 0 This is mrpe output" \
        >> "$MRPE_CACHE"
    echo -e "<<<my_plugin>>>\nThis is a custom plugin output" \
        >> "$PLUG_CACHE"

}

test_run_cached_plugin() {

    MTIME="$(stat -c %X "$PLUG_CACHE")"
    OUTPUT="$(run_cached "plugins_my_plugin" "180" "run_agent_plugin" "180/my_plugin")"

    assertEquals "$OUTPUT" \
"<<<my_plugin:cached($MTIME,180)>>>
This is a custom plugin output"

}

test_run_cached_local() {

    MTIME="$(stat -c %X "$LOCA_CACHE")"
    OUTPUT=$(run_cached "local_my_local_check" "180" "run_agent_locals" "_log_section_time 'local_180/my_local_check' './180/my_local_check'")

    assertEquals "$OUTPUT" \
"cached($MTIME,180) P \"This is local output\""

}

test_run_cached_mrpe() {

    descr="mrpetest"
    cmdline="this is the cmdline for the mrpe call"
    MTIME="$(stat -c %X "$MRPE_CACHE")"
    OUTPUT=$(run_cached "mrpe_$descr" "180" "_log_section_time 'mrpe_$descr' '$cmdline'")

    assertEquals "$OUTPUT" \
"<<<mrpe>>>
cached($MTIME,180) (my_check) Description 0 This is mrpe output"

}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
