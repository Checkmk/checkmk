#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree
from cmk.plugins.lib.cmctc import DETECT_CMCTC

# .1.3.6.1.4.1.2606.4.2.3.1.0 2
# .1.3.6.1.4.1.2606.4.2.3.2.0 CMC-TC-IOU
# .1.3.6.1.4.1.2606.4.2.3.3.0 60263
# .1.3.6.1.4.1.2606.4.2.3.4.0 1


def parse_cmctc_ports(string_table):
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


def inventory_cmctc_ports(parsed):
    for entry in parsed:
        yield entry, {}


def check_cmctc_ports(item, _no_params, parsed):
    port = parsed.get(item)
    if not port:
        return None

    status_map = {
        "ok": 0,
        "configuration changed": 1,
        "unit detected": 1,
        "error": 2,
        "quit from sensor unit": 2,
        "timeout": 2,
        "not available": 2,
        "supply voltage low": 2,
    }

    state = status_map.get(port["status"], 3)
    infotext = ("Status: %(status)s, " "Device type: %(type)s, " "Serial number: %(serial)s") % port

    return state, infotext


check_info["cmctc_ports"] = LegacyCheckDefinition(
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
    service_name="Port %s",
    discovery_function=inventory_cmctc_ports,
    check_function=check_cmctc_ports,
)
