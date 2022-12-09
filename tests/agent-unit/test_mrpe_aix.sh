#!/bin/bash
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

AGENT_AIX="${UNIT_SH_AGENTS_DIR}/check_mk_agent.aix"

# shellcheck source=../../agents/check_mk_agent.aix
MK_SOURCE_AGENT="true" source "$AGENT_AIX"

oneTimeSetUp() {

    MK_CONFDIR="${SHUNIT_TMPDIR}"
    CONFIGFILE="${SHUNIT_TMPDIR}/mrpe.cfg"

    cat > "${CONFIGFILE}" <<EOF
Foo_Application (interval=60:appendage=1) mrpe_plugin1 -w 60 -c 80
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
(mrpe_plugin1) Foo_Application 2 this is criticalYcmdline parameters: -w 60 -c 80\1
(mrpe_plugin2) Bar_Extender 0 this is OK\1
" | tr 'Y' '\1')"

    assertEquals "${expected}" "$(run_remote_plugins)"
}


# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
