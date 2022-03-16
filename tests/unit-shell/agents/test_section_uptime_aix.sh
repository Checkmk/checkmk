#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

AGENT_AIX="${UNIT_SH_AGENTS_DIR}/check_mk_agent.aix"

# shellcheck source=agents/check_mk_agent.aix
MK_SOURCE_AGENT="true" source "$AGENT_AIX"

test_checkmk_uptime() {

    uptime() { echo "12:55pm  up 105 days, 21 hrs,  2 users, load average: 0.26, 0.26, 0.26"; }
    assertEquals $'<<<uptime>>>\n9147600' "$(section_uptime)"

    uptime() { echo "1:41pm   up 105 days, 21:46,   2 users, load average: 0.28, 0.28, 0.27"; }
    assertEquals $'<<<uptime>>>\n9150360' "$(section_uptime)"

    uptime() { echo "05:26PM  up           1:16,    1 user,  load average: 0.33, 0.21, 0.20"; }
    assertEquals $'<<<uptime>>>\n4560' "$(section_uptime)"

    uptime() { echo "08:43AM  up 29 mins,           1 user,  load average: 0.09, 0.18, 0.21"; }
    assertEquals $'<<<uptime>>>\n1740' "$(section_uptime)"

    uptime() { echo "08:45AM  up 76 days,  34 mins, 1 user,  load average: 2.25, 2.43, 2.61"; }
    assertEquals $'<<<uptime>>>\n6568440' "$(section_uptime)"

    uptime() { echo "08:45AM  up 1 day,  34 mins, 1 user,  load average: 2.25, 2.43, 2.61"; }
    assertEquals $'<<<uptime>>>\n88440' "$(section_uptime)"

}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
