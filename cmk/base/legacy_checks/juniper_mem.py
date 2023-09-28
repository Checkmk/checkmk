#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.juniper_mem import juniper_mem_default_levels
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.juniper import DETECT_JUNIPER

# .1.3.6.1.4.1.2636.3.1.13.1.5.9.1.0.0 Routing Engine 0 --> JUNIPER-MIB::jnxOperatingDescr.9.1.0.0
# .1.3.6.1.4.1.2636.3.1.13.1.5.9.2.0.0 Routing Engine 1 --> JUNIPER-MIB::jnxOperatingDescr.9.2.0.0
# .1.3.6.1.4.1.2636.3.1.13.1.11.9.1.0.0 37 --> JUNIPER-MIB::jnxOperatingBuffer.9.1.0.0
# .1.3.6.1.4.1.2636.3.1.13.1.11.9.2.0.0 36 --> JUNIPER-MIB::jnxOperatingBuffer.9.2.0.0


def inventory_juniper_mem(info):
    return [(line[0], juniper_mem_default_levels) for line in info]


def check_juniper_mem(item, params, info):
    for descr, memory_str in info:
        if descr == item:
            memory_percent = float(memory_str)
            infotext = "%s%% used" % memory_str
            warn, crit = params
            if memory_percent >= crit:
                state = 2
            elif memory_percent >= warn:
                state = 1
            else:
                state = 0

            if state > 0:
                infotext += f" (warn/crit at {warn:.1f}%/{crit:.1f}%)"

            return state, infotext, [("mem_used_percent", memory_percent, warn, crit, 0, 100.0)]
    return None


check_info["juniper_mem"] = LegacyCheckDefinition(
    detect=DETECT_JUNIPER,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2636.3.1.13.1",
        oids=["5.9", "11.9"],
    ),
    service_name="Memory %s",
    discovery_function=inventory_juniper_mem,
    check_function=check_juniper_mem,
    check_ruleset_name="juniper_mem_modules",
)
