#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[var-annotated,list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
from cmk.base.config import factory_settings
from .humidity import check_humidity
from cmk.base.check_api import get_parsed_item_data
from .temperature import check_temperature
map_units = {"1": "c", "2": "f", "3": "k", "4": "%"}

map_dev_states = {
    "0": "invalid",
    "1": "normal",
    "2": "out of range low",
    "3": "out of range high",
    "4": "alarm low",
    "5": "alarm high",
}

map_readable_states = {
    "invalid": 3,
    "normal": 0,
    "out of range low": 2,
    "out of range high": 2,
    "alarm low": 2,
    "alarm high": 2,
}

factory_settings["hwg_humidity_defaultlevels"] = {"levels": (60, 70)}
factory_settings["hwg_temp_defaultlevels"] = {"levels": (30, 35)}


def parse_hwg(info):

    parsed = {}

    for index, descr, sensorstatus, current, unit in info:

        # Parse Humidity
        if int(sensorstatus) != 0 and map_units.get(unit, "") == "%":

            parsed.setdefault(
                index, {
                    "descr": descr,
                    "humidity": float(current),
                    "dev_status_name": map_dev_states.get(sensorstatus, "n.a."),
                    "dev_status": sensorstatus,
                })

        # Parse Temperature
        else:
            try:
                tempval = float(current)
            except ValueError:
                tempval = None

            parsed.setdefault(
                index, {
                    "descr": descr,
                    "dev_unit": map_units.get(unit),
                    "temperature": tempval,
                    "dev_status_name": map_dev_states.get(sensorstatus, ""),
                    "dev_status": sensorstatus,
                })

    return parsed


def inventory_hwg_humidity(parsed):

    for index, attrs in parsed.items():
        if attrs.get("humidity"):
            yield index, {}


@get_parsed_item_data
def check_hwg_humidity(item, params, parsed):

    status, infotext, perfdata = check_humidity(parsed["humidity"], params)
    infotext += " (Description: %s, Status: %s)" % (parsed["descr"], parsed["dev_status_name"])
    return status, infotext, perfdata


def inventory_hwg_temp(parsed):
    for index, attrs in parsed.items():
        if attrs.get("temperature") and attrs["dev_status_name"] not in ["invalid", ""]:
            yield index, {}


@get_parsed_item_data
def check_hwg_temp(item, params, parsed):

    state = map_readable_states.get(parsed["dev_status_name"], 3)
    state_readable = parsed["dev_status_name"]
    temp = parsed["temperature"]
    if temp is None:
        return state, "Status: %s" % state_readable

    state, infotext, perfdata = check_temperature(temp,
                                                  params,
                                                  "hwg_temp_%s" % item,
                                                  dev_unit=parsed["dev_unit"],
                                                  dev_status=state,
                                                  dev_status_name=state_readable)

    infotext += " (Description: %s, Status: %s)" % (parsed["descr"], parsed["dev_status_name"])
    return state, "%s" % infotext, perfdata
