#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

# .1.3.6.1.4.1.10876.2.1.1.1.1.2.1 Fan1 Fan Speed
# .1.3.6.1.4.1.10876.2.1.1.1.1.2.2 Fan2 Fan Speed
# ...
# .1.3.6.1.4.1.10876.2.1.1.1.1.2.6 Vcore Voltage
# .1.3.6.1.4.1.10876.2.1.1.1.1.2.7 CPU VTT Voltage
# .1.3.6.1.4.1.10876.2.1.1.1.1.3.1 0
# .1.3.6.1.4.1.10876.2.1.1.1.1.3.2 0
# ...
# .1.3.6.1.4.1.10876.2.1.1.1.1.3.6 1
# .1.3.6.1.4.1.10876.2.1.1.1.1.3.7 1
# .1.3.6.1.4.1.10876.2.1.1.1.1.4.1 3760
# .1.3.6.1.4.1.10876.2.1.1.1.1.4.2 1909
# ...
# .1.3.6.1.4.1.10876.2.1.1.1.1.4.6 1080
# .1.3.6.1.4.1.10876.2.1.1.1.1.4.7 1056
# ...
# .1.3.6.1.4.1.10876.2.1.1.1.1.5.6 1488
# .1.3.6.1.4.1.10876.2.1.1.1.1.5.7 1344
# .1.3.6.1.4.1.10876.2.1.1.1.1.6.1 291
# .1.3.6.1.4.1.10876.2.1.1.1.1.6.2 291
# ...
# .1.3.6.1.4.1.10876.2.1.1.1.1.11.1 RPM
# .1.3.6.1.4.1.10876.2.1.1.1.1.11.2 RPM
# ...
# .1.3.6.1.4.1.10876.2.1.1.1.1.11.6 mV
# .1.3.6.1.4.1.10876.2.1.1.1.1.11.7 mV
# .1.3.6.1.4.1.10876.2.1.1.1.1.12.1 0
# .1.3.6.1.4.1.10876.2.1.1.1.1.12.2 0
# ...
# .1.3.6.1.4.1.10876.2.1.1.1.1.12.6 0
# .1.3.6.1.4.1.10876.2.1.1.1.1.12.7 0
# .1.3.6.1.4.1.10876.2.2 0
# .1.3.6.1.4.1.10876.2.3 No problem.

# .
#   .--Health--------------------------------------------------------------.
#   |                    _   _            _ _   _                          |
#   |                   | | | | ___  __ _| | |_| |__                       |
#   |                   | |_| |/ _ \/ _` | | __| '_ \                      |
#   |                   |  _  |  __/ (_| | | |_| | | |                     |
#   |                   |_| |_|\___|\__,_|_|\__|_| |_|                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, any_of, contains, equals, exists, SNMPTree, StringTable

check_info = {}

DETECT_SUPERMICRO = any_of(
    equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.311.1.1.3.1.2"),
    all_of(contains(".1.3.6.1.2.1.1.1.0", "linux"), exists(".1.3.6.1.4.1.10876.2.1.1.1.1.2.1")),
)


def discover_supermicro_health(info):
    if info:
        return [(None, None)]
    return []


def check_supermicro_health(_no_item, _no_params, info):
    return int(info[0][0]), info[0][1]


def parse_supermicro(string_table: StringTable) -> StringTable:
    return string_table


check_info["supermicro"] = LegacyCheckDefinition(
    name="supermicro",
    parse_function=parse_supermicro,
    detect=DETECT_SUPERMICRO,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.10876.2",
        oids=["2", "3"],
    ),
    service_name="Overall Hardware Health",
    discovery_function=discover_supermicro_health,
    check_function=check_supermicro_health,
)

# .
#   .--Sensors-------------------------------------------------------------.
#   |                 ____                                                 |
#   |                / ___|  ___ _ __  ___  ___  _ __ ___                  |
#   |                \___ \ / _ \ '_ \/ __|/ _ \| '__/ __|                 |
#   |                 ___) |  __/ | | \__ \ (_) | |  \__ \                 |
#   |                |____/ \___|_| |_|___/\___/|_|  |___/                 |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_supermicro_sensors(info):
    for name, _sensor_type, _reading, _high, _low, _unit, _status in info:
        yield name, None


def check_supermicro_sensors(item, _no_params, info):
    class Type:
        _Fan, Voltage, Temperature, Status = ("0", "1", "2", "3")

    def worst_status(*args):
        order = [0, 1, 3, 2]
        return sorted(args, key=lambda x: order[x], reverse=True)[0]

    def expect_order(*args):
        return max(
            abs(x[0] - x[1][0]) for x in enumerate(sorted(enumerate(args), key=lambda x: x[1]))
        )

    for name, sensor_type, reading, high, low, unit, dev_status in info:
        if name == item:
            reading = float(reading)
            dev_status = int(dev_status)

            crit_upper = warn_upper = None
            status_high = status_low = 0
            if high:
                crit_upper = float(high)
                warn_upper = crit_upper * 0.95
                status_high = expect_order(reading, warn_upper, crit_upper)
            if low:
                crit_lower = float(low)
                warn_lower = crit_lower * 1.05
                status_low = expect_order(crit_lower, warn_lower, reading)

            perfvar = None

            # normalize values depending on sensor type
            if sensor_type == Type.Temperature:
                unit = "°%s" % unit
                perfvar = "temp"
            elif sensor_type == Type.Voltage:
                if unit == "mV":
                    # TODO: Could warn_upper and crit_upper be None here?
                    reading, warn_upper, crit_upper = (
                        x / 1000.0  # type: ignore[operator]
                        for x in (reading, warn_upper, crit_upper)
                    )
                    unit = "V"
                perfvar = "voltage"
            elif sensor_type == Type.Status:
                reading = "State %d" % int(reading)
                unit = ""

            return (
                worst_status(status_high, status_low, dev_status),
                f"{reading}{unit}",
                [(perfvar, reading, warn_upper, crit_upper)] if perfvar else [],
            )


def parse_supermicro_sensors(string_table: StringTable) -> StringTable:
    return string_table


check_info["supermicro_sensors"] = LegacyCheckDefinition(
    name="supermicro_sensors",
    parse_function=parse_supermicro_sensors,
    detect=DETECT_SUPERMICRO,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.10876.2.1.1.1.1",
        oids=["2", "3", "4", "5", "6", "11", "12"],
    ),
    service_name="Sensor %s",
    discovery_function=discover_supermicro_sensors,
    check_function=check_supermicro_sensors,
)

# .
#   .--SMART---------------------------------------------------------------.
#   |                   ____  __  __    _    ____ _____                    |
#   |                  / ___||  \/  |  / \  |  _ \_   _|                   |
#   |                  \___ \| |\/| | / _ \ | |_) || |                     |
#   |                   ___) | |  | |/ ___ \|  _ < | |                     |
#   |                  |____/|_|  |_/_/   \_\_| \_\|_|                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def format_item_supermicro_smart(name):
    return name.replace(r"\\\\.\\", "")


def discover_supermicro_smart(info):
    for _serial, name, _status in info:
        yield format_item_supermicro_smart(name), None


def check_supermicro_smart(item, _no_params, info):
    # note (only status 0 (OK) and 2 (Crit) are documented.
    # status 3 appears to indicate "unknown" as observed by a user.
    # It's likely - but not verified - that status 1 would indicate a non-
    # critical problem if it's used at all)
    status_map = {"0": "Healthy", "1": "Warning", "2": "Critical", "3": "Unknown"}
    for serial, name, status in info:
        if format_item_supermicro_smart(name) == item:
            return int(status), f"(S/N {serial}) {status_map[status]}"
    return None


def parse_supermicro_smart(string_table: StringTable) -> StringTable:
    return string_table


check_info["supermicro_smart"] = LegacyCheckDefinition(
    name="supermicro_smart",
    parse_function=parse_supermicro_smart,
    detect=DETECT_SUPERMICRO,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.10876.100.1.4.1",
        oids=["1", "2", "4"],
    ),
    service_name="SMART Health %s",
    discovery_function=discover_supermicro_smart,
    check_function=check_supermicro_smart,
)
