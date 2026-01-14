#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.mem import check_memory_element
from cmk.plugins.netscaler.agent_based.lib import SNMP_DETECT

check_info = {}

#
# Example Output:
# .1.3.6.1.4.1.5951.4.1.1.41.2.0  13
# .1.3.6.1.4.1.5951.4.1.1.41.4.0  7902


def discover_netscaler_mem(info):
    if info:
        yield None, {}


def check_netscaler_mem(_no_item, params, info):
    used_mem_perc, total_mem_mb = map(float, info[0])
    total_mem = total_mem_mb * 1024 * 1024
    used_mem = used_mem_perc / 100.0 * total_mem

    yield check_memory_element(
        "Usage",
        used_mem,
        total_mem,
        ("perc_used", params["levels"]),
        metric_name="mem_used",
    )


def parse_netscaler_mem(string_table: StringTable) -> StringTable:
    return string_table


check_info["netscaler_mem"] = LegacyCheckDefinition(
    name="netscaler_mem",
    parse_function=parse_netscaler_mem,
    detect=SNMP_DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5951.4.1.1.41",
        oids=["2", "4"],
    ),
    service_name="Memory",
    discovery_function=discover_netscaler_mem,
    check_function=check_netscaler_mem,
    check_ruleset_name="netscaler_mem",
    check_default_parameters={
        "levels": (80.0, 90.0),
    },
)
