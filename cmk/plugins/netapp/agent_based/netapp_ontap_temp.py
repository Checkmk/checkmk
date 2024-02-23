#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamDict
from cmk.plugins.netapp import models

Section = Mapping[str, models.ShelfTemperatureModel]

# <<<netapp_ontap_temp:sep(0)>>>
# {
#     "id": "10",
#     "temperature_sensors": [
#         {
#             "id": 1,
#             "temperature": 28.0,
#             "threshold": {
#                 "high": {"critical": 52.0, "warning": 47.0},
#                 "low": {"critical": 0.0, "warning": 5.0},
#             },
#         },
#         {
#             "id": 2,
#             "temperature": 27.0,
#             "threshold": {
#                 "high": {"critical": 60.0, "warning": 55.0},
#                 "low": {"critical": 0.0, "warning": 5.0},
#             },
#         },
#         {
#             "id": 3,
#             "temperature": 27.0,
#             "threshold": {
#                 "high": {"critical": 60.0, "warning": 55.0},
#                 "low": {"critical": 0.0, "warning": 5.0},
#             },
#         },
#         {
#             "id": 4,
#             "temperature": 27.0,
#             "threshold": {
#                 "high": {"critical": 60.0, "warning": 55.0},
#                 "low": {"critical": 0.0, "warning": 5.0},
#             },
#         },
#         {
#             "id": 5,
#             "temperature": 27.0,
#             "threshold": {
#                 "high": {"critical": 60.0, "warning": 55.0},
#                 "low": {"critical": 0.0, "warning": 5.0},
#             },
#         },
#         {
#             "id": 6,
#             "temperature": 29.0,
#             "threshold": {
#                 "high": {"critical": 62.0, "warning": 57.0},
#                 "low": {"critical": 5.0, "warning": 10.0},
#             },
#         },
#         {
#             "id": 7,
#             "temperature": 47.0,
#             "threshold": {
#                 "high": {"critical": 100.0, "warning": 95.0},
#                 "low": {"critical": 5.0, "warning": 10.0},
#             },
#         },
#         {
#             "id": 8,
#             "temperature": 29.0,
#             "threshold": {
#                 "high": {"critical": 62.0, "warning": 57.0},
#                 "low": {"critical": 5.0, "warning": 10.0},
#             },
#         },
#         {
#             "id": 9,
#             "temperature": 46.0,
#             "threshold": {
#                 "high": {"critical": 100.0, "warning": 95.0},
#                 "low": {"critical": 5.0, "warning": 10.0},
#             },
#         },
#         {
#             "id": 10,
#             "temperature": 36.0,
#             "threshold": {
#                 "high": {"critical": 90.0, "warning": 85.0},
#                 "low": {"critical": 0.0, "warning": 5.0},
#             },
#         },
#         {
#             "id": 11,
#             "temperature": 38.0,
#             "threshold": {
#                 "high": {"critical": 90.0, "warning": 85.0},
#                 "low": {"critical": 0.0, "warning": 5.0},
#             },
#         },
#     ],
# }


def parse_netapp_ontap_temp(string_table: StringTable) -> Section:
    return {
        fan.item_name(): fan
        for line in string_table
        if (fan := models.ShelfTemperatureModel.model_validate_json(line[0]))
    }


agent_section_netapp_ontap_temp = AgentSection(
    name="netapp_ontap_temp",
    parse_function=parse_netapp_ontap_temp,
)


def discovery_netapp_ontap_temp(section: Section) -> DiscoveryResult:
    for sensor_name, sensor in section.items():
        yield (
            Service(item=f"Ambient Shelf Sensor {sensor_name}")
            if sensor.ambient
            else Service(item=f"Internal Shelf Sensor {sensor_name}")
        )


def check_netapp_ontap_temp(item: str, params: TempParamDict, section: Section) -> CheckResult:
    if not (sensor := section.get(item.split()[-1])):
        return

    dev_levels = (
        (
            float(sensor.high_warning),
            float(sensor.high_critical),
        )
        if sensor.high_warning is not None and sensor.high_critical is not None
        else None
    )
    dev_levels_lower = (
        (
            float(sensor.low_warning),
            float(sensor.low_critical),
        )
        if sensor.low_warning is not None and sensor.low_critical is not None
        else None
    )

    yield from check_temperature(
        reading=sensor.temperature,
        params=params,
        unique_name=f"Temperature sensor {sensor.item_name()}",
        dev_levels=dev_levels,
        dev_levels_lower=dev_levels_lower,
        value_store=get_value_store(),
    )


check_plugin_netapp_ontap_temp = CheckPlugin(
    name="netapp_ontap_temp",
    service_name="Temperature %s",
    sections=["netapp_ontap_temp"],
    discovery_function=discovery_netapp_ontap_temp,
    check_function=check_netapp_ontap_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
