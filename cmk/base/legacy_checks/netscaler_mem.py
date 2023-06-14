#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.mem import check_memory_element
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.netscaler import SNMP_DETECT

#
# Example Output:
# .1.3.6.1.4.1.5951.4.1.1.41.2.0  13
# .1.3.6.1.4.1.5951.4.1.1.41.4.0  7902

netscaler_mem_default_levels = (80.0, 90.0)


def inventory_netscaler_mem(info):
    if info:
        return [(None, netscaler_mem_default_levels)]
    return []


def check_netscaler_mem(_no_item, params, info):
    used_mem_perc, total_mem_mb = map(float, info[0])
    total_mem = total_mem_mb * 1024 * 1024
    used_mem = used_mem_perc / 100.0 * total_mem

    yield check_memory_element(
        "Usage",
        used_mem,
        total_mem,
        ("perc_used", params),
        metric_name="mem_used",
    )


check_info["netscaler_mem"] = LegacyCheckDefinition(
    detect=SNMP_DETECT,
    check_function=check_netscaler_mem,
    discovery_function=inventory_netscaler_mem,
    service_name="Memory",
    check_ruleset_name="netscaler_mem",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5951.4.1.1.41",
        oids=["2", "4"],
    ),
)
