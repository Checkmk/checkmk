#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import any_of, OIDEnd, SNMPTree, startswith, StringTable

check_info = {}

qlogic_sanbox_status_map = [
    "undefined",  # 0
    "unknown",  # 1
    "other",  # 2
    "ok",  # 3
    "warning",  # 4
    "failed",  # 5
]


def parse_qlogic_sanbox(string_table: StringTable) -> StringTable:
    return string_table


check_info["qlogic_sanbox"] = LegacyCheckDefinition(
    name="qlogic_sanbox",
    parse_function=parse_qlogic_sanbox,
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3873.1.14"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3873.1.8"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.3.94.1.8.1",
        oids=["3", "4", "6", "7", "8", OIDEnd()],
    ),
)

#   .--temp----------------------------------------------------------------.
#   |                       _                                              |
#   |                      | |_ ___ _ __ ___  _ __                         |
#   |                      | __/ _ \ '_ ` _ \| '_ \                        |
#   |                      | ||  __/ | | | | | |_) |                       |
#   |                       \__\___|_| |_| |_| .__/                        |
#   |                                        |_|                           |
#   '----------------------------------------------------------------------'


def inventory_qlogic_sanbox_temp(info):
    inventory = []
    for (
        sensor_name,
        _sensor_status,
        _sensor_message,
        sensor_type,
        sensor_characteristic,
        sensor_id,
    ) in info:
        sensor_id = sensor_id.replace("16.0.0.192.221.48.", "").replace(".0.0.0.0.0.0.0.0", "")
        if (
            sensor_type == "8"
            and sensor_characteristic == "3"
            and sensor_name != "Temperature Status"
        ):
            inventory.append((sensor_id, None))
    return inventory


def check_qlogic_sanbox_temp(item, _no_params, info):
    for (
        _sensor_name,
        sensor_status,
        sensor_message,
        _sensor_type,
        _sensor_characteristic,
        sensor_id,
    ) in info:
        sensor_id = sensor_id.replace("16.0.0.192.221.48.", "").replace(".0.0.0.0.0.0.0.0", "")
        if sensor_id == item:
            sensor_status = int(sensor_status)
            if sensor_status < 0 or sensor_status >= len(qlogic_sanbox_status_map):
                sensor_status_descr = str(sensor_status)
            else:
                sensor_status_descr = qlogic_sanbox_status_map[int(sensor_status)]

            if sensor_status == 3:
                status = 0
            elif sensor_status == 4:
                status = 1
            elif sensor_status == 5:
                status = 2
            else:
                status = 3

            if sensor_message.endswith(" degrees C"):
                temp = int(sensor_message.replace(" degrees C", ""))
                perfdata = [("temp", str(temp) + "C")]
            else:
                perfdata = []

            return (
                status,
                f"Sensor {sensor_id} is at {sensor_message} and reports status {sensor_status_descr}",
                perfdata,
            )
    return 3, "No sensor %s found" % item


check_info["qlogic_sanbox.temp"] = LegacyCheckDefinition(
    name="qlogic_sanbox_temp",
    service_name="Temperature Sensor %s",
    sections=["qlogic_sanbox"],
    discovery_function=inventory_qlogic_sanbox_temp,
    check_function=check_qlogic_sanbox_temp,
)

# .
#   .--power supplies------------------------------------------------------.
#   |                                                      _ _             |
#   | _ __   _____      _____ _ __   ___ _   _ _ __  _ __ | (_) ___  ___   |
#   || '_ \ / _ \ \ /\ / / _ \ '__| / __| | | | '_ \| '_ \| | |/ _ \/ __|  |
#   || |_) | (_) \ V  V /  __/ |    \__ \ |_| | |_) | |_) | | |  __/\__ \  |
#   || .__/ \___/ \_/\_/ \___|_|    |___/\__,_| .__/| .__/|_|_|\___||___/  |
#   ||_|                                      |_|   |_|                    |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_qlogic_sanbox_psu(info):
    inventory = []
    for (
        _sensor_name,
        _sensor_status,
        _sensor_message,
        sensor_type,
        _sensor_characteristic,
        sensor_id,
    ) in info:
        sensor_id = sensor_id.replace("16.0.0.192.221.48.", "").replace(".0.0.0.0.0.0.0.0", "")
        if sensor_type == "5":
            inventory.append((sensor_id, None))
    return inventory


def check_qlogic_sanbox_psu(item, _no_params, info):
    for (
        _sensor_name,
        sensor_status,
        _sensor_message,
        _sensor_type,
        _sensor_characteristic,
        sensor_id,
    ) in info:
        sensor_id = sensor_id.replace("16.0.0.192.221.48.", "").replace(".0.0.0.0.0.0.0.0", "")
        if sensor_id == item:
            sensor_status = int(sensor_status)
            if sensor_status < 0 or sensor_status >= len(qlogic_sanbox_status_map):
                sensor_status_descr = str(sensor_status)
            else:
                sensor_status_descr = qlogic_sanbox_status_map[int(sensor_status)]

            if sensor_status == 3:
                status = 0
            elif sensor_status == 4:
                status = 1
            elif sensor_status == 5:
                status = 2
            else:
                status = 3

            return status, f"Power Supply {sensor_id} reports status {sensor_status_descr}"
    return 3, "No sensor %s found" % item


check_info["qlogic_sanbox.psu"] = LegacyCheckDefinition(
    name="qlogic_sanbox_psu",
    service_name="PSU %s",
    sections=["qlogic_sanbox"],
    discovery_function=inventory_qlogic_sanbox_psu,
    check_function=check_qlogic_sanbox_psu,
)
