#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.bluecat.lib import DETECT_BLUECAT

_OPER_STATE_MAP = {
    1: "running normally",
    2: "not running",
    3: "currently starting",
    4: "currently stopping",
    5: "fault",
}


def parse_bluecat_command_server(string_table: StringTable) -> StringTable | None:
    return string_table or None


def discover_bluecat_command_server(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_bluecat_command_server(
    params: Mapping[str, Any],
    section: StringTable,
) -> CheckResult:
    oper_state = int(section[0][0])
    state = State.OK
    if oper_state in params["oper_states"]["warning"]:
        state = State.WARN
    elif oper_state in params["oper_states"]["critical"]:
        state = State.CRIT
    yield Result(state=state, summary=f"Command Server is {_OPER_STATE_MAP[oper_state]}")


snmp_section_bluecat_command_server = SimpleSNMPSection(
    name="bluecat_command_server",
    parse_function=parse_bluecat_command_server,
    detect=DETECT_BLUECAT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13315.3.1.7.2.1",
        oids=["1"],
    ),
)

check_plugin_bluecat_command_server = CheckPlugin(
    name="bluecat_command_server",
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
