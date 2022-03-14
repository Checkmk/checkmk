#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, List, Mapping, Optional

from ..agent_based_api.v1 import Service, type_defs

Variable = List[str]
DiscoveryParams = Mapping[str, bool]
CheckParams = Mapping[str, Any]

Devices = Dict[str, str]
SensorType = str
Sensor = Dict[str, Any]
Sensors = Dict[str, Sensor]
Section = Dict[SensorType, Sensors]


def discovery_default_parameters() -> DiscoveryParams:
    return {"use_sensor_description": False}


def discover_cmciii_sensors(
    type_: str, params: DiscoveryParams, parsed: Section
) -> type_defs.DiscoveryResult:
    for id_, entry in parsed[type_].items():
        yield Service(item=get_item(id_, params, entry), parameters={"_item_key": id_})


def get_item(id_: str, params: DiscoveryParams, sensor: Sensor) -> str:
    if params.get("use_sensor_description", False):
        return "%s-%s %s" % (sensor["_location_"], sensor["_index_"], sensor["DescName"])
    return id_


def get_sensor(item: str, params: CheckParams, sensors: Sensors) -> Optional[Sensor]:
    # This function is used for compatibility whith discovered services that do
    # not use _item_key in the params (yet).
    if params and (params_key := params.get("_item_key")):
        return sensors.get(params_key)
    return sensors.get(item)
