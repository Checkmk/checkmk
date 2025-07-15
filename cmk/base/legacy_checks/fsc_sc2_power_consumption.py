#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.base.check_legacy_includes.fsc import DETECT_FSC_SC2

check_info = {}

# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.4.1.3.1 "CPU1 Power"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.4.1.3.2 "CPU2 Power"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.4.1.4.1 "HDD Power"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.4.1.7.1 "System Power"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.4.1.10.1 "PSU1 Power"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.4.1.10.2 "PSU2 Power"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.4.1.224.1 "Total Power"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.4.1.224.2 "Total Power Out"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.5.1.3.1 5
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.5.1.3.2 0
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.5.1.4.1 8
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.5.1.7.1 50
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.5.1.10.1 52
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.5.1.10.2 40
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.5.1.224.1 92
# .1.3.6.1.4.1.231.2.10.2.2.10.6.7.1.5.1.224.2 68


def parse_fsc_sc2_power_consumption(info):
    parsed: dict = {}
    for designation, value in info:
        # sometimes the device does not return a value
        if not value:
            parsed.setdefault(
                designation, {"device_state": (3, "Error on device while reading value")}
            )
        else:
            parsed.setdefault(designation, {"power": int(value)})
    return parsed


def discover_fsc_sc2_power_consumption(section):
    yield from ((item, {}) for item in section)


check_info["fsc_sc2_power_consumption"] = LegacyCheckDefinition(
    name="fsc_sc2_power_consumption",
    detect=DETECT_FSC_SC2,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.2.10.2.2.10.6.7.1",
        oids=["4", "5"],
    ),
    parse_function=parse_fsc_sc2_power_consumption,
    service_name="Power Comsumption %s",
    discovery_function=discover_fsc_sc2_power_consumption,
    check_function=check_elphase,
    check_ruleset_name="el_inphase",
)
