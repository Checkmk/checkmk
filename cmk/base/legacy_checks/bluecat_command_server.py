#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.bluecat.lib import DETECT_BLUECAT

check_info = {}


def discover_bluecat_command_server(info):
    return [(None, None)]


def check_bluecat_command_server(item, params, info):
    oper_state = int(info[0][0])
    oper_states = {
        1: "running normally",
        2: "not running",
        3: "currently starting",
        4: "currently stopping",
        5: "fault",
    }
    state = 0
    if oper_state in params["oper_states"]["warning"]:
        state = 1
    elif oper_state in params["oper_states"]["critical"]:
        state = 2
    yield state, "Command Server is %s" % oper_states[oper_state]


def parse_bluecat_command_server(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["bluecat_command_server"] = LegacyCheckDefinition(
    name="bluecat_command_server",
    parse_function=parse_bluecat_command_server,
    detect=DETECT_BLUECAT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13315.3.1.7.2.1",
        oids=["1"],
    ),
    service_name="Command Server",
    discovery_function=discover_bluecat_command_server,
    check_function=check_bluecat_command_server,
    check_ruleset_name="bluecat_command_server",
    check_default_parameters={
        "oper_states": {
            "warning": [2, 3, 4],
            "critical": [5],
        },
    },
)
