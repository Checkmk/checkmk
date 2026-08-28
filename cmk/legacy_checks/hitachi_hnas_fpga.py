#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.hitachi_hnas.lib import DETECT


def parse_hitachi_hnas_fpga(string_table: StringTable) -> StringTable:
    return string_table


def discover_hitachi_hnas_fpga(section: StringTable) -> DiscoveryResult:
    for clusternode, id_, name, _util in section:
        yield Service(item=f"{clusternode}.{id_} {name}")


def check_hitachi_hnas_fpga(
    item: str, params: Mapping[str, tuple[float, float]], section: StringTable
) -> CheckResult:
    warn, crit = params["levels"]

    for clusternode, id_, name, util_str in section:
        if f"{clusternode}.{id_} {name}" != item:
            continue

        util = float(util_str)
        yield Result(
            state=State.CRIT if util > crit else State.WARN if util > warn else State.OK,
            summary=f"PNode {clusternode} FPGA {id_} {name} utilization is {util}%",
        )
        yield Metric("fpga_util", util, levels=(warn, crit), boundaries=(0.0, 100.0))
        return

    yield Result(state=State.UNKNOWN, summary=f"No utilization found for FPGA {item}")


snmp_section_hitachi_hnas_fpga = SimpleSNMPSection(
    name="hitachi_hnas_fpga",
    parse_function=parse_hitachi_hnas_fpga,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.6.1.4.1",
        oids=["1", "2", "3", "4"],
    ),
)


check_plugin_hitachi_hnas_fpga = CheckPlugin(
    name="hitachi_hnas_fpga",
    service_name="FPGA %s",
    discovery_function=discover_hitachi_hnas_fpga,
    check_function=check_hitachi_hnas_fpga,
    check_ruleset_name="fpga_utilization",
    check_default_parameters={"levels": (80.0, 90.0)},
)
