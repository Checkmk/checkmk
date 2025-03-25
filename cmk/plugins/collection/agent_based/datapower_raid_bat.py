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
from cmk.plugins.lib.datapower import DETECT


def inventory_datapower_raid_bat(section: StringTable) -> DiscoveryResult:
    for controller_id, _bat_type, _serial, _name, _status in section:
        yield Service(item=controller_id)


def check_datapower_raid_bat(item: str, section: StringTable) -> CheckResult:
    datapower_raid_bat_status = {
        "1": (State.OK, "charging"),
        "2": (State.WARN, "discharging"),
        "3": (State.CRIT, "i2c errors detected"),
        "4": (State.OK, "learn cycle active"),
        "5": (State.CRIT, "learn cycle failed"),
        "6": (State.OK, "learn cycle requested"),
        "7": (State.CRIT, "learn cycle timeout"),
        "8": (State.CRIT, "pack missing"),
        "9": (State.CRIT, "temperature high"),
        "10": (State.CRIT, "voltage low"),
        "11": (State.WARN, "periodic learn required"),
        "12": (State.WARN, "remaining capacity low"),
        "13": (State.CRIT, "replace pack"),
        "14": (State.OK, "normal"),
        "15": (State.WARN, "undefined"),
    }
    datapower_raid_bat_type = {
        "1": "no battery present",
        "2": "ibbu",
        "3": "bbu",
        "4": "zcrLegacyBBU",
        "5": "itbbu3",
        "6": "ibbu08",
        "7": "unknown",
    }
    for controller_id, bat_type, serial, name, status in section:
        if item == controller_id:
            state, state_txt = datapower_raid_bat_status[status]
            type_txt = datapower_raid_bat_type[bat_type]
            infotext = f"Status: {state_txt}, Name: {name}, Type: {type_txt}, Serial: {serial}"
            yield Result(state=state, summary=infotext)
            return


def parse_datapower_raid_bat(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_datapower_raid_bat = SimpleSNMPSection(
    name="datapower_raid_bat",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14685.3.1.258.1",
        oids=["1", "2", "3", "4", "5"],
    ),
    parse_function=parse_datapower_raid_bat,
)
check_plugin_datapower_raid_bat = CheckPlugin(
    name="datapower_raid_bat",
    service_name="Raid Battery %s",
    discovery_function=inventory_datapower_raid_bat,
    check_function=check_datapower_raid_bat,
)
