#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ..agent_based_api.v1 import Service


def discovery_default_parameters():
    return {'use_sensor_description': False}


def discover_cmciii_sensors(type_, params, parsed):
    for id_, entry in parsed[type_].items():
        yield Service(item=get_item(id_, params, entry), parameters={'_item_key': id_})


def get_item(id_, params, sensor):
    if params.get('use_sensor_description', False) and (description := sensor.get('DescName')):
        return description
    return id_


def get_sensor(item, params, sensors):
    # This function is used for compatibility whith discovered services that do
    # not use _item_key in the params (yet).
    if params and (params_key := params.get('_item_key')):
        return sensors.get(params_key)
    return sensors.get(item)
