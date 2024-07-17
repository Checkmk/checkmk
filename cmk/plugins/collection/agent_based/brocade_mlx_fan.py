#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.brocade import DETECT_MLX


def brocade_mlx_fan_combine_item(id_, descr):
    if descr == "" or "(RPM " in descr:
        return id_
    return f"{id_} {descr}"


def inventory_brocade_mlx_fan(section: StringTable) -> DiscoveryResult:
    inventory = []
    for fan_id, fan_descr, fan_state in section:
        # Only add Fans who are present
        if fan_state != "1":
            inventory.append((brocade_mlx_fan_combine_item(fan_id, fan_descr), None))
    yield from [Service(item=item, parameters=parameters) for (item, parameters) in inventory]


def check_brocade_mlx_fan(item: str, section: StringTable) -> CheckResult:
    for fan_id, fan_descr, fan_state in section:
        if brocade_mlx_fan_combine_item(fan_id, fan_descr) == item:
            if fan_state == "2":
                yield Result(state=State.OK, summary="Fan reports state: normal")
                return
            if fan_state == "3":
                yield Result(state=State.CRIT, summary="Fan reports state: failure")
                return
            if fan_state == "1":
                yield Result(state=State.UNKNOWN, summary="Fan reports state: other")
                return
            yield Result(
                state=State.UNKNOWN, summary="Fan reports an unhandled state (%s)" % fan_state
            )
            return
    yield Result(state=State.UNKNOWN, summary="Fan not found")
    return


def parse_brocade_mlx_fan(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_brocade_mlx_fan = SimpleSNMPSection(
    name="brocade_mlx_fan",
    detect=DETECT_MLX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1991.1.1.1.3.1.1",
        oids=["1", "2", "3"],
    ),
    parse_function=parse_brocade_mlx_fan,
)
check_plugin_brocade_mlx_fan = CheckPlugin(
    name="brocade_mlx_fan",
    service_name="Fan %s",
    discovery_function=inventory_brocade_mlx_fan,
    check_function=check_brocade_mlx_fan,
)
