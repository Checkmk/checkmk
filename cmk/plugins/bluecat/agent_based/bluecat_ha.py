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
    1: "standalone",
    2: "active",
    3: "passiv",
    4: "stopped",
    5: "stopping",
    6: "becoming active",
    7: "becomming passive",
    8: "fault",
}


def parse_bluecat_ha(string_table: StringTable) -> StringTable | None:
    return string_table or None


def discover_bluecat_ha(section: StringTable) -> DiscoveryResult:
    # Only add if device is not in standalone mode
    if section[0][0] != "1":
        yield Service()


def check_bluecat_ha(
    params: Mapping[str, Any],
    section: StringTable,
) -> CheckResult:
    oper_state = int(section[0][0])
    state = State.OK
    if oper_state in params["oper_states"]["warning"]:
        state = State.WARN
    elif oper_state in params["oper_states"]["critical"]:
        state = State.CRIT
    yield Result(state=state, summary=f"State is {_OPER_STATE_MAP[oper_state]}")


snmp_section_bluecat_ha = SimpleSNMPSection(
    name="bluecat_ha",
    parse_function=parse_bluecat_ha,
    detect=DETECT_BLUECAT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13315.3.1.5.2.1",
        oids=["1"],
    ),
)

check_plugin_bluecat_ha = CheckPlugin(
    name="bluecat_ha",
    service_name="HA State",
    discovery_function=discover_bluecat_ha,
    check_function=check_bluecat_ha,
    check_ruleset_name="bluecat_ha",
    check_default_parameters={
        "oper_states": {
            "warning": [5, 6, 7],
            "critical": [8, 4],
        },
    },
)
