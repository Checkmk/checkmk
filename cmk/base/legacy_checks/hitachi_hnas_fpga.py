#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import DiscoveryResult, Service, SNMPTree, StringTable
from cmk.plugins.lib.hitachi_hnas import DETECT

check_info = {}


def discover_hitachi_hnas_fpga(string_table: StringTable) -> DiscoveryResult:
    for clusternode, id_, name, _util in string_table:
        yield Service(item=clusternode + "." + id_ + " " + name)


def check_hitachi_hnas_fpga(item, params, info):
    warn, crit = params["levels"]
    rc = 0

    for clusternode, id_, name, util in info:
        if clusternode + "." + id_ + " " + name == item:
            util = float(util)
            if util > warn:
                rc = 1
            if util > crit:
                rc = 2
            perfdata = [("fpga_util", str(util) + "%", warn, crit, 0, 100)]
            return (
                rc,
                f"PNode {clusternode} FPGA {id_} {name} utilization is {util}%",
                perfdata,
            )

    return 3, "No utilization found for FPGA %s" % item


def parse_hitachi_hnas_fpga(string_table: StringTable) -> StringTable:
    return string_table


check_info["hitachi_hnas_fpga"] = LegacyCheckDefinition(
    name="hitachi_hnas_fpga",
    parse_function=parse_hitachi_hnas_fpga,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.6.1.4.1",
        oids=["1", "2", "3", "4"],
    ),
    service_name="FPGA %s",
    discovery_function=discover_hitachi_hnas_fpga,
    check_function=check_hitachi_hnas_fpga,
    check_ruleset_name="fpga_utilization",
    check_default_parameters={"levels": (80.0, 90.0)},
)
