#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

AGENT_LINUX="${UNIT_SH_AGENTS_DIR}/check_mk_agent.linux"

# shellcheck source=agents/check_mk_agent.linux
MK_SOURCE_AGENT="true" source "$AGENT_LINUX"

oneTimeSetUp() {

    CONFIGFILE="${SHUNIT_TMPDIR}/mrpe.cfg"

    cat >"${CONFIGFILE}" <<EOF
Foo_Application (ignored=parameter) mrpe_plugin1 -w 60 -c 80
Bar_Extender mrpe_plugin2 -s -X -w 4:5
EOF

    STDIN_CONFIGFILE="${SHUNIT_TMPDIR}/mrpe_stdin.cfg"
    cat >"${STDIN_CONFIGFILE}" <<EOF
First_Check mrpe_plugin_reads_stdin
Second_Check mrpe_plugin2
EOF
}

mrpe_plugin1() {
    echo "this is critical"
    echo "cmdline parameters: $*"
    return 2
}

mrpe_plugin2() {
    echo "this is OK"
}

mrpe_plugin_reads_stdin() {
    # Simulate a plugin that reads from stdin.
    read -r _ignored || true
    echo "this is OK"
}

test_run_remote_plugins() {
    expected="$(printf "<<<mrpe>>>
(mrpe_plugin1) Foo_Application 2 this is criticalYcmdline parameters: -w 60 -c 80
<<<mrpe>>>
(mrpe_plugin2) Bar_Extender 0 this is OK
" | tr 'Y' '\1')"

    assertEquals "${expected}" "$(run_remote_plugins "${CONFIGFILE}")"
}

test_run_remote_plugins_stdin_does_not_steal_entries() {
    # A plugin that reads from stdin must not consume subsequent mrpe.cfg lines
    # from the pipe, which would cause later entries to be skipped.
    expected="$(printf "<<<mrpe>>>
(mrpe_plugin_reads_stdin) First_Check 0 this is OK
<<<mrpe>>>
(mrpe_plugin2) Second_Check 0 this is OK
")"

    assertEquals "${expected}" "$(run_remote_plugins "${STDIN_CONFIGFILE}")"
}

test__mrpe_get_interval() {
    assertEquals "132" "$(_mrpe_get_interval "(interval=132) some command")"
    assertEquals "132" "$(_mrpe_get_interval "(foo=true:interval=132:bar=no) some command")"
    assertEquals "" "$(_mrpe_get_interval "(foobar=132) some command")"
    assertEquals "" "$(_mrpe_get_interval "some command")"
}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
