#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.hitachi_hnas.lib import DETECT

check_info = {}


def format_hitachi_hnas_name(nodeid, sensorid, new_format):
    # net item format is used in 1.2.7i? and newer
    if new_format:
        return f"Node {nodeid} Sensor {sensorid}"
    return f"{nodeid}.{sensorid}"


def discover_hitachi_hnas_temp(info):
    for clusternode, id_, _status, _temp in info:
        yield format_hitachi_hnas_name(clusternode, id_, True), None


def check_hitachi_hnas_temp(item, params, info):
    temp_status_map = (
        ("", 3),  # 0
        ("ok", 0),  # 1
        ("tempWarning", 1),  # 2
        ("tempSevere", 2),  # 3
        ("tempSensorFailed", 2),  # 4
        ("tempSensorWarning", 1),  # 5
        ("unknown", 3),  # 6
    )

    for clusternode, id_, status, temp in info:
        new_format = item.startswith("Node")
        if format_hitachi_hnas_name(clusternode, id_, new_format) == item:
            status = int(status)
            temp = int(temp)

            if status == 0 or status >= len(temp_status_map):
                return 3, "unidentified status %s" % status, []

            return check_temperature(
                temp,
                params,
                "hitachi_hnas_temp_%s" % item,
                dev_status=temp_status_map[status][1],
                dev_status_name="Unit: %s" % temp_status_map[status][0],
            )
    return 3, "No sensor found", []


def parse_hitachi_hnas_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["hitachi_hnas_temp"] = LegacyCheckDefinition(
    name="hitachi_hnas_temp",
    parse_function=parse_hitachi_hnas_temp,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.1.2.1.9.1",
        oids=["1", "2", "3", "4"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_hitachi_hnas_temp,
    check_function=check_hitachi_hnas_temp,
    check_ruleset_name="temperature",
)
