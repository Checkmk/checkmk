#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

AGENT_LINUX="${UNIT_SH_AGENTS_DIR}/check_mk_agent.linux"

# shellcheck source=agents/check_mk_agent.linux
MK_SOURCE_AGENT="true" source "$AGENT_LINUX"

oneTimeSetUp() {

    set_up_get_epoch

    export CACHEDIR="${SHUNIT_TMPDIR}/cache"
    mkdir -p "$CACHEDIR"

    PLUG_CACHE="$CACHEDIR/plugins_my_plugin.cache"
    LOCA_CACHE="$CACHEDIR/local_my_local_check.cache"
    MRPE_CACHE="$CACHEDIR/mrpe_mrpetest.cache"

    # create some caches
    # similar/duplicate lines are on purpose, because sed is for pros.

    # local plugin
    {
        echo 'P "This is local output without custom cache info"'
        # the header is against the spec, but users do it so often that we ignore it
        echo '<<<local>>>'
        echo '<<<local>>>'
        echo 'cached(123,456) P "leave my custom cache info alone!"'
        echo 'cached(123,456) P "leave my custom cache info alone as well!"'
        echo 'P "This is more output without custom cache info"'
    } >"$LOCA_CACHE"

    # mrpe plugin
    {
        # Note that mrpe includes a section header
        echo "<<<mrpe>>>"
        echo "(my_check) Description 0 This is mrpe output"
    } >"$MRPE_CACHE"

    # agent plugin
    {
        echo "<<<my_plugin_section>>>"
        echo "This is a custom plugin output"
        echo "<<<my_plugin_section2:cached(123,456)>>>"
        echo "<<<my_plugin_section3:cached(123,789)>>>"
        echo "This is a custom plugin output with own cache info"
    } >"$PLUG_CACHE"

}

test_run_cached_plugin() {

    MTIME="$(stat -c %X "$PLUG_CACHE")"
    OUTPUT="$(_run_cached_internal "plugins_my_plugin" 170 180 540 360 "run_agent_plugin" "170/my_plugin")"

    expected() {
        echo "<<<my_plugin_section:cached($MTIME,180)>>>"
        echo "This is a custom plugin output"
        echo "<<<my_plugin_section2:cached(123,456)>>>"
        echo "<<<my_plugin_section3:cached(123,789)>>>"
        echo "This is a custom plugin output with own cache info"
    }

    assertEquals "$(expected)" "$OUTPUT"

}

test_run_cached_local() {

    MTIME="$(stat -c %X "$LOCA_CACHE")"
    OUTPUT=$(_run_cached_internal "local_my_local_check" 170 180 540 360 "run_agent_locals" "_log_section_time 'local_170/my_local_check' './170/my_local_check'")

    expected() {
        echo "cached($MTIME,180) P \"This is local output without custom cache info\""
        echo "<<<local>>>"
        echo "<<<local>>>"
        echo "cached(123,456) P \"leave my custom cache info alone!\""
        echo "cached(123,456) P \"leave my custom cache info alone as well!\""
        echo "cached($MTIME,180) P \"This is more output without custom cache info\""
    }

    assertEquals "$(expected)" "$OUTPUT"

}

test_run_cached_mrpe() {

    descr="mrpetest"
    cmdline="this is the cmdline for the mrpe call"
    MTIME="$(stat -c %X "$MRPE_CACHE")"
    OUTPUT=$(_run_cached_internal "mrpe_$descr" 170 180 540 360 "_log_section_time 'mrpe_$descr' '$cmdline'")

    assertEquals "<<<mrpe>>>
cached($MTIME,180) (my_check) Description 0 This is mrpe output" "$OUTPUT"

}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
