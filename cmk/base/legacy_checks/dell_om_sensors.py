#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.dell.lib import DETECT_OPENMANAGE

check_info = {}


def dell_om_sensors_item(name):
    return name.replace("Temp", "").strip()


def discover_dell_om_sensors(info):
    for line in info:
        if line[3]:
            yield dell_om_sensors_item(line[3]), {}


def check_dell_om_sensors(item, params, info):
    sensor_states = {
        1: "other",
        2: "unknown",
        10: "failed",
    }
    for (
        idx,
        sensor_state,
        reading,
        location_name,
        dev_crit,
        dev_warn,
        dev_warn_lower,
        dev_crit_lower,
    ) in info:
        if item == idx or dell_om_sensors_item(location_name) == item:
            sensor_state = int(sensor_state)
            if sensor_state in [1, 2, 10]:
                return 2, "Sensor is: " + sensor_states[sensor_state]

            temp = int(reading) / 10.0

            dev_warn, dev_crit, dev_warn_lower, dev_crit_lower = (
                float(v) / 10 if v else None
                for v in [dev_warn, dev_crit, dev_warn_lower, dev_crit_lower]
            )
            if not dev_warn_lower:
                dev_warn_lower = dev_crit_lower
            if not dev_warn:
                dev_warn = dev_crit

            return check_temperature(
                temp,
                params,
                "dell_om_sensors_%s" % item,
                dev_levels=(dev_warn, dev_crit),
                dev_levels_lower=(dev_warn_lower, dev_crit_lower),
            )
    return None


def parse_dell_om_sensors(string_table: StringTable) -> StringTable:
    return string_table


check_info["dell_om_sensors"] = LegacyCheckDefinition(
    name="dell_om_sensors",
    parse_function=parse_dell_om_sensors,
    detect=DETECT_OPENMANAGE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.1.700.20.1",
        oids=["2", "5", "6", "8", "10", "11", "12", "13"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_dell_om_sensors,
    check_function=check_dell_om_sensors,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (50.0, 60.0)},
)
