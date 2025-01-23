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
from cmk.plugins.lib.cmctc import DETECT_CMCTC

# .1.3.6.1.4.1.2606.4.2.3.1.0 2
# .1.3.6.1.4.1.2606.4.2.3.2.0 CMC-TC-IOU
# .1.3.6.1.4.1.2606.4.2.3.3.0 60263
# .1.3.6.1.4.1.2606.4.2.3.4.0 1


Section = Mapping[str, Mapping]


def parse_cmctc_ports(string_table: Sequence[StringTable]) -> Section | None:
    def parse_single_port(port_info):
        type_map = {
            "1": "not available",
            "2": "IO",
            "3": "Access",
            "4": "Climate",
            "5": "FCS",
            "6": "RTT",
            "7": "RTC",
            "8": "PSM",
            "9": "PSM8",
            "10": "PSM metered",
            "11": "IO wireless",
            "12": "PSM6 Schuko",
            "13": "PSM6C19",
            "14": "Fuel Cell",
            "15": "DRC",
            "16": "TE cooler",
            "17": "PSM32 metered",
            "18": "PSM8x8",
            "19": "PSM6x6 Schuko",
            "20": "PSM6x6C19",
        }

        status_map = {
            "1": "ok",
            "2": "error",
            "3": "configuration changed",
            "4": "quit from sensor unit",
            "5": "timeout",
            "6": "unit detected",
            "7": "not available",
            "8": "supply voltage low",
        }

        device_type, description, serial_number, device_status = port_info

        parsed = {
            "type": type_map.get(device_type),
            "status": status_map.get(device_status),
            "serial": serial_number,
        }

        if parsed["status"] == "not available":
            return None

        return description, parsed

    if not all(string_table):
        return None

    parsed = {}
    # cmctc_lcp uses port numbers the range 3-6.
    # Therefore, we start counting at 3 here as well
    # to stay consistent.
    for number, (port_info,) in enumerate(string_table, 3):
        parsed_port = parse_single_port(port_info)
        if parsed_port:
            description, entry = parsed_port
            name = "%d %s" % (number, description)
            parsed[name] = entry

    return parsed


def inventory_cmctc_ports(section: Section) -> DiscoveryResult:
    for entry in section:
        yield Service(item=entry)


def check_cmctc_ports(item: str, section: Section) -> CheckResult:
    if (port := section.get(item)) is None:
        return

    status_map = {
        "ok": State.OK,
        "configuration changed": State.WARN,
        "unit detected": State.WARN,
        "error": State.CRIT,
        "quit from sensor unit": State.CRIT,
        "timeout": State.CRIT,
        "not available": State.CRIT,
        "supply voltage low": State.CRIT,
    }

    state = status_map.get(port["status"], State.UNKNOWN)
    infotext = ("Status: %(status)s, Device type: %(type)s, Serial number: %(serial)s") % port

    yield Result(state=state, summary=infotext)


snmp_section_cmctc_ports = SNMPSection(
    name="cmctc_ports",
    detect=DETECT_CMCTC,
    fetch=[
        SNMPTree(
            base=f".1.3.6.1.4.1.2606.4.2.{unit}",
            oids=["1", "2", "3", "4"],
        )
        for unit in [
            "3",  # cmcTcStatusSensorUnit1
            "4",  # cmcTcStatusSensorUnit2
            "5",  # cmcTcStatusSensorUnit3
            "6",  # cmcTcStatusSensorUnit4
        ]
    ],
    parse_function=parse_cmctc_ports,
)
check_plugin_cmctc_ports = CheckPlugin(
    name="cmctc_ports",
    service_name="Port %s",
    discovery_function=inventory_cmctc_ports,
    check_function=check_cmctc_ports,
)
