#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass

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
from cmk.plugins.lib.datapower import DETECT


@dataclass(frozen=True)
class Fan:
    state: str
    state_txt: str
    speed: str


Section = Mapping[str, Fan]


_FAN_ID_TO_NAME = {
    "1": "CPU 1",
    "2": "CPU 2",
    "3": "Chassis 1",
    "4": "Chassis 2",
    "5": "Chassis 3",
    "6": "Chassis 4",
    "7": "Chassis 5",
    "8": "Chassis 6",
    "9": "Chassis 7",
    "10": "Chassis 8",
    "11": "Tray 1 Fan 1",
    "12": "Tray 1 Fan 2",
    "13": "Tray 1 Fan 3",
    "14": "Tray 1 Fan 4",
    "15": "Tray 2 Fan 1",
    "16": "Tray 2 Fan 2",
    "17": "Tray 2 Fan 3",
    "18": "Tray 2 Fan 4",
    "19": "Tray 3 Fan 1",
    "20": "Tray 3 Fan 2",
    "21": "Tray 3 Fan 3",
    "22": "Tray 3 Fan 4",
    "23": "Hard Disk Tray Fan 1",
    "24": "Hard Disk Tray Fan 2",
    "25": "1a",
    "26": "1b",
    "27": "2a",
    "28": "2b",
    "29": "3a",
    "30": "3b",
    "31": "4a",
    "32": "4b",
    "33": "1",
    "34": "2",
    "35": "3",
}

_FAN_STATE_TO_TXT = {
    "1": "reached lower non-recoverable limit",
    "2": "reached lower critical limit",
    "3": "reached lower non-critical limit",
    "4": "operating normally",
    "5": "reached upper non-critical limit",
    "6": "reached upper critical limit",
    "7": "reached upper non-recoverable limit",
    "8": "failure",
    "9": "no reading",
    "10": "Invalid",
}


def parse_datapower_fan(string_table: StringTable) -> Section:
    return {
        _FAN_ID_TO_NAME[fan_id]: Fan(
            state,
            _FAN_STATE_TO_TXT[state],
            speed,
        )
        for fan_id, speed, state in string_table
    }


snmp_section_datapower_fan = SimpleSNMPSection(
    name="datapower_fan",
    parse_function=parse_datapower_fan,
    detect=DETECT,
    fetch=SNMPTree(
        ".1.3.6.1.4.1.14685.3.1.97.1",
        [
            "1",  # dpStatusEnvironmentalFanSensorsFanID
            "2",  # dpStatusEnvironmentalFanSensorsFanSpeed
            "4",  # dpStatusEnvironmentalFanSensorsReadingStatus
        ],
    ),
)


def inventory_datapower_fan(section: Section) -> DiscoveryResult:
    yield from (Service(item=fan_name) for fan_name in section)


_FAN_STATE_TO_MON_STATE = {
    "1": State.CRIT,
    "2": State.CRIT,
    "3": State.WARN,
    "4": State.OK,
    "5": State.WARN,
    "6": State.CRIT,
    "7": State.CRIT,
    "8": State.CRIT,
    "9": State.CRIT,
    "10": State.WARN,
}


def check_datapower_fan(item: str, section: Section) -> CheckResult:
    if not (fan := section.get(item)):
        return
    yield Result(
        state=_FAN_STATE_TO_MON_STATE[fan.state], summary=f"{fan.state_txt}, {fan.speed} rpm"
    )


check_plugin_datapower_fan = CheckPlugin(
    name="datapower_fan",
    service_name="Fan %s",
    discovery_function=inventory_datapower_fan,
    check_function=check_datapower_fan,
)
