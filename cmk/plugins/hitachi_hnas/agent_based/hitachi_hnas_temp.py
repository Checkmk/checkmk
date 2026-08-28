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
from cmk.plugins.hitachi_hnas.lib import DETECT
from cmk.plugins.lib.temperature import check_temperature, TempParamType

_TEMP_STATUS_MAP = (
    ("", State.UNKNOWN),  # 0
    ("ok", State.OK),  # 1
    ("tempWarning", State.WARN),  # 2
    ("tempSevere", State.CRIT),  # 3
    ("tempSensorFailed", State.CRIT),  # 4
    ("tempSensorWarning", State.WARN),  # 5
    ("unknown", State.UNKNOWN),  # 6
)


def format_hitachi_hnas_name(nodeid: str, sensorid: str, new_format: bool) -> str:
    # net item format is used in 1.2.7i? and newer
    if new_format:
        return f"Node {nodeid} Sensor {sensorid}"
    return f"{nodeid}.{sensorid}"


def parse_hitachi_hnas_temp(string_table: StringTable) -> StringTable:
    return string_table


def discover_hitachi_hnas_temp(section: StringTable) -> DiscoveryResult:
    for clusternode, id_, _status, _temp in section:
        yield Service(item=format_hitachi_hnas_name(clusternode, id_, True))


def check_hitachi_hnas_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    for clusternode, id_, status_str, temp_str in section:
        new_format = item.startswith("Node")
        if format_hitachi_hnas_name(clusternode, id_, new_format) != item:
            continue

        status = int(status_str)
        if status == 0 or status >= len(_TEMP_STATUS_MAP):
            yield Result(state=State.UNKNOWN, summary=f"unidentified status {status}")
            return

        name, state = _TEMP_STATUS_MAP[status]
        yield from check_temperature(
            int(temp_str),
            params,
            unique_name=f"hitachi_hnas_temp_{item}",
            value_store=get_value_store(),
            dev_status=state.value,
            dev_status_name=f"Unit: {name}",
        )
        return

    yield Result(state=State.UNKNOWN, summary="No sensor found")


snmp_section_hitachi_hnas_temp = SimpleSNMPSection(
    name="hitachi_hnas_temp",
    parse_function=parse_hitachi_hnas_temp,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.1.2.1.9.1",
        oids=["1", "2", "3", "4"],
    ),
)


check_plugin_hitachi_hnas_temp = CheckPlugin(
    name="hitachi_hnas_temp",
    service_name="Temperature %s",
    discovery_function=discover_hitachi_hnas_temp,
    check_function=check_hitachi_hnas_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
