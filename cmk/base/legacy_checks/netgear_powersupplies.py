#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# .1.3.6.1.4.1.4526.10.43.1.7.1.3.1.0 2 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesPowSupplyItemState.1.0
# .1.3.6.1.4.1.4526.10.43.1.7.1.3.1.1 1 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesPowSupplyItemState.1.1
# .1.3.6.1.4.1.4526.10.43.1.7.1.3.2.0 2 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesPowSupplyItemState.2.0
# .1.3.6.1.4.1.4526.10.43.1.7.1.3.2.1 1 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesPowSupplyItemState.2.1


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree
from cmk.plugins.netgear.lib import DETECT_NETGEAR

check_info = {}


def parse_netgear_powersupplies(string_table):
    parsed = {}
    for oid_end, sstate in string_table:
        parsed.setdefault("%s" % oid_end.replace(".", "/"), sstate)
    return parsed


def discover_netgear_powersupplies(parsed):
    return [
        (sensorname, {}) for sensorname, sensorinfo in parsed.items() if sensorinfo not in ["1"]
    ]


def check_netgear_powersupplies(item, params, parsed):
    map_states = {
        "1": (1, "not present"),
        "2": (0, "operational"),
        "3": (2, "failed"),
    }
    if item in parsed:
        state, state_readable = map_states[parsed[item]]
        return state, "Status: %s" % state_readable
    return None


check_info["netgear_powersupplies"] = LegacyCheckDefinition(
    name="netgear_powersupplies",
    detect=DETECT_NETGEAR,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.4526.10.43.1.7.1",
        oids=[OIDEnd(), "3"],
    ),
    parse_function=parse_netgear_powersupplies,
    service_name="Power Supply %s",
    discovery_function=discover_netgear_powersupplies,
    check_function=check_netgear_powersupplies,
)
