#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import all_of, DiscoveryResult, Service, startswith

Variable = list[str]
DiscoveryParams = Mapping[str, bool]
CheckParams = Mapping[str, Any]

Devices = dict[str, str]
SensorType = str
Sensor = dict[str, Any]
Sensors = dict[str, Sensor]
Section = dict[SensorType, Sensors]


DETECT_CMCIII_LCP = all_of(
    startswith(".1.3.6.1.2.1.1.1.0", "Rittal LCP"),
    startswith(".1.3.6.1.4.1.2606.7.4.2.2.1.3.2.6", "Air.Temperature.DescName"),
)


def discovery_default_parameters() -> DiscoveryParams:
    return {"use_sensor_description": False}


def discover_cmciii_sensors(
    type_: str, params: DiscoveryParams, parsed: Section
) -> DiscoveryResult:
    for id_, entry in parsed[type_].items():
        yield Service(item=get_item(id_, params, entry), parameters={"_item_key": id_})


def get_item(id_: str, params: DiscoveryParams, sensor: Sensor) -> str:
    if params.get("use_sensor_description", False):
        return "{}-{} {}".format(sensor["_location_"], sensor["_index_"], sensor["DescName"])
    return id_


def get_sensor(item: str, params: CheckParams, sensors: Sensors) -> Sensor | None:
    # This function is used for compatibility whith discovered services that do
    # not use _item_key in the params (yet).
    if params and (params_key := params.get("_item_key")):
        return sensors.get(params_key)
    return sensors.get(item)
