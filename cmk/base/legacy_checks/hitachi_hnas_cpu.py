#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import DiscoveryResult, Service, SNMPTree, StringTable
from cmk.plugins.lib.hitachi_hnas import DETECT

check_info = {}


def discover_hitachi_hnas_cpu(string_table: StringTable) -> DiscoveryResult:
    for id_, _util in string_table:
        yield Service(item=id_)


def check_hitachi_hnas_cpu(item, params, info):
    warn, crit = params["levels"]
    rc = 0

    for id_, util in info:
        if id_ == item:
            util = float(util)
            if util > warn:
                rc = 1
            if util > crit:
                rc = 2
            perfdata = [("cpu_util", str(util) + "%", warn, crit, 0, 100)]
            return rc, "CPU utilization is %s%%" % util, perfdata

    return 3, "No CPU utilization found"


def parse_hitachi_hnas_cpu(string_table: StringTable) -> StringTable:
    return string_table


check_info["hitachi_hnas_cpu"] = LegacyCheckDefinition(
    name="hitachi_hnas_cpu",
    parse_function=parse_hitachi_hnas_cpu,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.6.1.2.1",
        oids=["1", "3"],
    ),
    service_name="CPU utilization PNode %s",
    discovery_function=discover_hitachi_hnas_cpu,
    check_function=check_hitachi_hnas_cpu,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={"levels": (80.0, 90.0)},
)
