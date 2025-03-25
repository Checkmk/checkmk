#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing
from collections import abc

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib import hp_proliant

CONDITION_MAP: typing.Final = {
    "1": Result(  # the status could not be determined or not present.
        state=State.UNKNOWN, summary='State: "other"'
    ),
    "2": Result(state=State.OK, summary='State: "ok"'),  # operating normally
    "3": Result(  # component is outside of normal operating range.
        state=State.CRIT, summary='State: "degraded"'
    ),
    "4": Result(  # component detects condition that could damage system
        state=State.CRIT, summary='State: "failed"'
    ),
}


class Psu(typing.NamedTuple):
    chassis: str
    bay: str
    condition: str
    used: int
    max_: int


class PsuTotal(typing.NamedTuple):
    used: int
    max_: int


class Params(typing.TypedDict, total=True):
    levels: tuple[float, float]


Section = abc.Mapping[str, Psu | PsuTotal]


def parse_hp_proliant_psu(string_table: StringTable) -> Section:
    section: dict[str, Psu | PsuTotal] = {}
    for chassis, bay, present, cond, used, capacity_maximum in string_table:
        if present != "3" or capacity_maximum == "0":
            continue
        item = f"{chassis}/{bay}"
        try:
            section[item] = Psu(chassis, bay, cond, int(used), int(capacity_maximum))
        except ValueError:
            pass
    if section:
        section["Total"] = PsuTotal(
            sum(v.used for v in section.values()), sum(v.max_ for v in section.values())
        )
    return section


snmp_section_hp_proliant_psu = SimpleSNMPSection(
    name="hp_proliant_psu",
    parse_function=parse_hp_proliant_psu,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.6.2.9.3.1",
        oids=[
            "1",  # cpqHeFltTolPowerSupplyChassis
            "2",  # cpqHeFltTolPowerSupplyBay
            "3",  # cpqHeFltTolPowerSupplyPresent
            "4",  # cpqHeFltTolPowerSupplyCondition
            "7",  # cpqHeFltTolPowerSupplyCapacityUsed
            "8",  # cpqHeFltTolPowerSupplyCapacityMaximum
        ],
    ),
    detect=hp_proliant.DETECT,
)


def discover_hp_proliant_psu(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_hp_proliant_psu(item: str, params: Params, section: Section) -> CheckResult:
    if (psu := section.get(item)) is None:
        return
    if isinstance(psu, Psu):
        yield Result(state=State.OK, summary=f"Chassis {psu.chassis}/Bay {psu.bay}")
        yield CONDITION_MAP[psu.condition]

    yield Result(state=State.OK, summary=f"Usage: {psu.used}/{psu.max_} Watts")
    yield Metric(name="power_usage", value=psu.used)
    yield from check_levels_v1(
        psu.used * 100.0 / psu.max_,
        levels_upper=params["levels"],
        metric_name="power_usage_percentage",
        label="Percentage",
        render_func=render.percent,
    )


check_plugin_hp_proliant_psu = CheckPlugin(
    name="hp_proliant_psu",
    service_name="HW PSU %s",
    check_function=check_hp_proliant_psu,
    discovery_function=discover_hp_proliant_psu,
    check_default_parameters={"levels": (80.0, 90.0)},
)
