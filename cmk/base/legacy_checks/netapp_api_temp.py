#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.netapp_api import netapp_api_parse_lines
from cmk.base.check_legacy_includes.temperature import check_temperature_list, CheckTempKwargs
from cmk.base.config import check_info

# <<<netapp_api_temp:sep(9)>>>
# temp-sensor-list 11 temp-sensor-current-condition normal_temperature_range  temp-sensor-is-ambient true temp-sensor-low-warning 5   temp-sensor-hi-warning 40   temp-sensor-hi-critical 42  temp-sensor-current-temperature 24  temp-sensor-element-no 1    temp-sensor-low-critical 0  temp-sensor-is-error false


def parse_netapp_api_temp(string_table):
    return netapp_api_parse_lines(
        string_table, custom_keys=["temp-sensor-list", "temp-sensor-element-no"]
    )


def inventory_netapp_api_temp(parsed):
    shelfs = {x.split(".")[0] for x in parsed}
    for shelf in shelfs:
        yield "Internal Shelf %s" % shelf, {}
        yield "Ambient Shelf %s" % shelf, {}


def check_netapp_api_temp(item, params, parsed):
    is_ambient = "true" if item.startswith("Ambient") else "false"
    item_no = item.split()[-1]
    required_keys = {
        "temp-sensor-current-temperature",
        "temp-sensor-element-no",
        "temp-sensor-low-warning",
        "temp-sensor-low-critical",
        "temp-sensor-hi-warning",
        "temp-sensor-hi-critical",
    }
    sensors = (
        {k: int(values[k]) for k in required_keys}
        for name, values in parsed.items()
        if required_keys.issubset(values.keys())  #
        if name.split(".")[0] == item_no  #
        if values.get("temp-sensor-is-not-installed") != "true"  #
        if values.get("temp-sensor-is-ambient") == is_ambient
    )

    sensorlist: list[tuple[str, int, CheckTempKwargs]] = [
        (
            f"{item_no}/{sensor['temp-sensor-element-no']}",
            sensor["temp-sensor-current-temperature"],
            {
                "dev_levels": (
                    sensor["temp-sensor-hi-warning"],
                    sensor["temp-sensor-hi-critical"],
                ),
                "dev_levels_lower": (
                    sensor["temp-sensor-low-warning"],
                    sensor["temp-sensor-low-critical"],
                ),
            },
        )
        for sensor in sensors
    ]

    if not sensorlist:
        yield 0, "No temperature sensors assigned to this filer"
        return

    yield from check_temperature_list(sensorlist, params)


check_info["netapp_api_temp"] = LegacyCheckDefinition(
    parse_function=parse_netapp_api_temp,
    service_name="Temperature %s",
    discovery_function=inventory_netapp_api_temp,
    check_function=check_netapp_api_temp,
    check_ruleset_name="temperature",
)
