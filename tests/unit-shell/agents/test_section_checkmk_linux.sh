#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


AGENT_LINUX="${UNIT_SH_AGENTS_DIR}/check_mk_agent.linux"


# shellcheck source=../../agents/check_mk_agent.linux
MK_SOURCE_AGENT="true" source "$AGENT_LINUX"


test_checkmk_section () {

    checkmk_section="$(section_checkmk)"

    assertContains "$checkmk_section" "<<<check_mk>>>"
    assertContains "$checkmk_section" "AgentOS: linux"

}


# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
