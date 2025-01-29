#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.brocade import DETECT_MLX

Section = Mapping[str, Mapping[str, str]]


def parse_brocade_mlx_power(string_table: Sequence[StringTable]) -> Section:
    parsed = {}

    if len(string_table[1]) > 0:
        # .1.3.6.1.4.1.1991.1.1.1.2.2.1
        for power_id, power_desc, power_state in string_table[1]:
            if power_state != "1":
                parsed[power_id] = {"desc": power_desc, "state": power_state}
    else:
        # .1.3.6.1.4.1.1991.1.1.1.2.1.1
        for power_id, power_desc, power_state in string_table[0]:
            if power_state != "1":
                parsed[power_id] = {"desc": power_desc, "state": power_state}
    return parsed


snmp_section_brocade_mlx_power = SNMPSection(
    name="brocade_mlx_power",
    detect=DETECT_MLX,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.1991.1.1.1.2.1.1",
            oids=["1", "2", "3"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.1991.1.1.1.2.2.1",
            oids=["2", "3", "4"],
        ),
    ],
    parse_function=parse_brocade_mlx_power,
)


def inventory_brocade_mlx_power(section: Section) -> DiscoveryResult:
    yield from (Service(item=powersupply_id) for powersupply_id in section)


def check_brocade_mlx_power(item: str, section: Section) -> CheckResult:
    if (powersupply_data := section.get(item)) is None:
        return

    match powersupply_data["state"]:
        case "2":
            yield Result(state=State.OK, summary="Power supply reports state: normal")
        case "3":
            yield Result(state=State.CRIT, summary="Power supply reports state: failure")
        case "1":
            yield Result(state=State.UNKNOWN, summary="Power supply reports state: other")
        case other:
            yield Result(
                state=State.UNKNOWN,
                summary=f"Power supply reports an unknown state ({other})",
            )


check_plugin_brocade_mlx_power = CheckPlugin(
    name="brocade_mlx_power",
    service_name="Power supply %s",
    discovery_function=inventory_brocade_mlx_power,
    check_function=check_brocade_mlx_power,
)
