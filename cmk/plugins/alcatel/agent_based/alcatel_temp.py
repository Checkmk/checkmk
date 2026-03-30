#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.alcatel.lib import DETECT_ALCATEL
from cmk.plugins.lib.temperature import check_temperature, TempParamDict, TempParamType

type Section = StringTable


def parse_alcatel_temp(string_table: StringTable) -> Section:
    return string_table


def discover_alcatel_temp(section: Section) -> DiscoveryResult:
    with_slot = len(section) != 1
    for index, row in enumerate(section):
        for oid, name in enumerate(["Board", "CPU"]):
            if row[oid] != "0":
                if with_slot:
                    yield Service(item=f"Slot {index + 1} {name}")
                else:
                    yield Service(item=name)


def check_alcatel_temp(item: str, params: TempParamType, section: Section) -> CheckResult:
    if len(section) == 1:
        slot_index = 0
    else:
        slot = int(item.split()[1])
        slot_index = slot - 1
    sensor = item.rsplit(maxsplit=1)[-1]
    items = {"Board": 0, "CPU": 1}
    try:
        # If multiple switches are stacked and one of them is
        # not reachable, prevent an exception
        temp_celsius = int(section[slot_index][items[sensor]])
    except Exception:
        yield Result(state=State.UNKNOWN, summary="Sensor not found")
        return
    yield from check_temperature(
        reading=float(temp_celsius),
        params=params,
        unique_name=item,
        value_store=get_value_store(),
    )


snmp_section_alcatel_temp = SimpleSNMPSection(
    name="alcatel_temp",
    detect=DETECT_ALCATEL,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6486.800.1.1.1.3.1.1.3.1",
        oids=["4", "5"],
    ),
    parse_function=parse_alcatel_temp,
)


check_plugin_alcatel_temp = CheckPlugin(
    name="alcatel_temp",
    service_name="Temperature %s",
    discovery_function=discover_alcatel_temp,
    check_function=check_alcatel_temp,
    check_ruleset_name="temperature",
    check_default_parameters=TempParamDict(levels=(45.0, 50.0)),
)
