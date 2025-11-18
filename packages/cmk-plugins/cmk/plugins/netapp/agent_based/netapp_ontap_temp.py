#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections import defaultdict
from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.temperature import (
    aggregate_temperature_results,
    check_temperature,
    parse_levels,
    TemperatureSensor,
    TempParamDict,
)
from cmk.plugins.netapp import models

Section = Mapping[str, Sequence[models.ShelfTemperatureModel]]

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
    section = defaultdict(list)

    for line in string_table:
        sensor = models.ShelfTemperatureModel.model_validate_json(line[0])
        if not sensor.consider_installed():
            continue
        section[f"{'Ambient' if sensor.ambient else 'Internal'} Shelf {sensor.list_id}"].append(
            sensor
        )

    return section


agent_section_netapp_ontap_temp = AgentSection(
    name="netapp_ontap_temp",
    parse_function=parse_netapp_ontap_temp,
)


def discovery_netapp_ontap_temp(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def _check_netapp_ontap_temp(
    item: str, params: TempParamDict, section: Section, value_store: MutableMapping[str, Any]
) -> CheckResult:
    if not (sensors := section.get(item)):
        return

    checksensors = []
    for sensor in sensors:
        if sensor.state == "ok":
            assert sensor.temperature is not None
            checksensors.append(
                TemperatureSensor(
                    id=sensor.item_name(),
                    temp=sensor.temperature,
                    result=check_temperature(
                        sensor.temperature,
                        params,
                        dev_levels=parse_levels(
                            (
                                sensor.high_warning,
                                sensor.high_critical,
                            )
                        ),
                        dev_levels_lower=parse_levels(
                            (
                                sensor.low_warning,
                                sensor.low_critical,
                            )
                        ),
                    ).reading,
                )
            )

    yield from aggregate_temperature_results(checksensors, params, value_store)
    failed_sensors = [s for s in sensors if s.state != "ok"]
    if failed_sensors:
        failed_sensor_names = ", ".join(s.item_name() for s in failed_sensors)
        yield Result(
            state=State.CRIT,
            summary=f"Additional failed sensors: {len(failed_sensors)} ({failed_sensor_names})",
        )


def check_netapp_ontap_temp(item: str, params: TempParamDict, section: Section) -> CheckResult:
    yield from _check_netapp_ontap_temp(item, params, section, get_value_store())


check_plugin_netapp_ontap_temp = CheckPlugin(
    name="netapp_ontap_temp",
    service_name="Temperature %s",
    sections=["netapp_ontap_temp"],
    discovery_function=discovery_netapp_ontap_temp,
    check_function=check_netapp_ontap_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
