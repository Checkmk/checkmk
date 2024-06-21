#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example SNMP Walk
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.3.1.6 Leckagekontrolle-RZ4
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.3.2.5 Pumpe 1 RZ4
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.3.2.6 Pumpe 2 RZ4
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.4.1.6 Kaeltepark RZ4
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.4.2.5 Kaeltepark RZ4
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.4.2.6 Kaeltepark RZ4
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.5.1.6 2
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.5.2.5 2
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.5.2.6 2
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.7.1.6 1
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.7.2.5 1
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.7.2.6 1
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.8.1.6 2
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.8.2.5 2
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.8.2.6 2


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import OIDEnd, SNMPTree
from cmk.plugins.lib.apc import DETECT


def parse_apc_netbotz_drycontact(string_table):
    parsed = {}

    state_map = {
        "1": ("Closed high mem", 2),
        "2": ("Open low mem", 0),
        "3": ("Disabled", 1),
        "4": ("Not applicable", 3),
    }

    for idx, inst, loc, state in string_table:
        parsed[inst + " " + idx] = {
            "location": loc,
            "state": state_map.get(state, ("unknown[%s]" % state, 3)),
        }

    return parsed


def check_apc_netbotz_drycontact(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    state_readable, state = data["state"]
    loc = data["location"]
    if loc:
        loc_info = "[%s] " % loc
    else:
        loc_info = ""
    yield state, f"{loc_info}State: {state_readable}"


def discover_apc_netbotz_drycontact(section):
    yield from ((item, {}) for item in section)


check_info["apc_netbotz_drycontact"] = LegacyCheckDefinition(
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.10.4.3.2.1",
        oids=[OIDEnd(), "3", "4", "5"],
    ),
    parse_function=parse_apc_netbotz_drycontact,
    service_name="DryContact %s",
    discovery_function=discover_apc_netbotz_drycontact,
    check_function=check_apc_netbotz_drycontact,
)
