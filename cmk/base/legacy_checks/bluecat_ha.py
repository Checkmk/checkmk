#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import DiscoveryResult, Service, SNMPTree, StringTable
from cmk.plugins.lib.bluecat import DETECT_BLUECAT

check_info = {}


def discover_bluecat_ha(section: StringTable) -> DiscoveryResult:
    # Only add if device is not in standalone mode
    if section and section[0][0] != "1":
        yield Service()


def check_bluecat_ha(_no_item, params, info):
    oper_state = int(info[0][0])
    oper_states = {
        1: "standalone",
        2: "active",
        3: "passiv",
        4: "stopped",
        5: "stopping",
        6: "becoming active",
        7: "becomming passive",
        8: "fault",
    }

    state = 0
    if oper_state in params["oper_states"]["warning"]:
        state = 1
    elif oper_state in params["oper_states"]["critical"]:
        state = 2
    yield state, "State is %s" % oper_states[oper_state]


def parse_bluecat_ha(string_table: StringTable) -> StringTable:
    return string_table


check_info["bluecat_ha"] = LegacyCheckDefinition(
    name="bluecat_ha",
    parse_function=parse_bluecat_ha,
    detect=DETECT_BLUECAT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13315.3.1.5.2.1",
        oids=["1"],
    ),
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
