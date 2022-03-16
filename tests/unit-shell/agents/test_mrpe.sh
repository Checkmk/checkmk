#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

AGENT_LINUX="${UNIT_SH_AGENTS_DIR}/check_mk_agent.linux"

# shellcheck source=../../agents/check_mk_agent.linux
MK_SOURCE_AGENT="true" source "$AGENT_LINUX"

oneTimeSetUp() {

    CONFIGFILE="${SHUNIT_TMPDIR}/mrpe.cfg"

    cat >"${CONFIGFILE}" <<EOF
Foo_Application (ignored=parameter) mrpe_plugin1 -w 60 -c 80
Bar_Extender mrpe_plugin2 -s -X -w 4:5
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

test_run_remote_plugins() {
    expected="$(printf "<<<mrpe>>>
(mrpe_plugin1) Foo_Application 2 this is criticalYcmdline parameters: -w 60 -c 80
<<<mrpe>>>
(mrpe_plugin2) Bar_Extender 0 this is OK
" | tr 'Y' '\1')"

    assertEquals "${expected}" "$(run_remote_plugins "${CONFIGFILE}")"
}

test__mrpe_get_interval() {
    assertEquals "132" "$(_mrpe_get_interval "(interval=132) some command")"
    assertEquals "132" "$(_mrpe_get_interval "(foo=true:interval=132:bar=no) some command")"
    assertEquals "" "$(_mrpe_get_interval "(foobar=132) some command")"
    assertEquals "" "$(_mrpe_get_interval "some command")"
}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
