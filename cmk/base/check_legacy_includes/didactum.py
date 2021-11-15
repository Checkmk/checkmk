#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# type: ignore[attr-defined]  # TODO: see which are needed in this file

from .elphase import check_elphase
from .humidity import check_humidity
from .temperature import check_temperature


def scan_didactum(oid):
    return "didactum" in oid(".1.3.6.1.2.1.1.1.0").lower()


# elements (not excatly sensors!) can be:
# temperature, analog voltage, usb-cam, reader, GSM modem, magnet,
# smoke, unknown, induct relay, pushbutton, timer
def parse_didactum_sensors(info):
    map_states = {
        "alarm": 2,
        "high alarm": 2,
        "low alarm": 2,
        "warning": 1,
        "high warning": 1,
        "low warning": 1,
        "normal": 0,
        "not connected": 3,
        "on": 0,
        "off": 3,
    }

    parsed = {}
    for line in info:
        ty, name, status = line[:3]
        if status in map_states:
            state = map_states[status]
            state_readable = status
        else:
            state = 3
            state_readable = "unknown[%s]" % status

        parsed.setdefault(ty, {})
        parsed[ty].setdefault(
            name,
            {
                "state": state,
                "state_readable": state_readable,
            },
        )

        if len(line) >= 4:
            value_str = line[3]
            if value_str.isdigit():
                value = int(value_str)
            else:
                try:
                    value = float(value_str)
                except ValueError:
                    value = value_str
            parsed[ty][name].update({"value": value})

        if len(line) == 8:
            crit_lower, warn_lower, warn, crit = line[4:]
            parsed[ty][name].update(
                {
                    "levels": (float(warn), float(crit)),
                    "levels_lower": (float(warn_lower), float(crit_lower)),
                }
            )

    return parsed


def inventory_didactum_sensors(parsed, what):
    return [
        (sensorname, {})
        for sensorname, attrs in parsed.get(what, {}).items()
        if attrs["state_readable"] not in ["off", "not connected"]
    ]


def check_didactum_sensors_temp(item, params, parsed):
    if item in parsed["temperature"]:
        data = parsed["temperature"][item]
        return check_temperature(
            data["value"],
            params,
            "didactum_can_sensors_analog_temp.%s" % item,
            dev_levels=data["levels"],
            dev_levels_lower=data["levels_lower"],
            dev_status=data["state"],
            dev_status_name=data["state_readable"],
        )


def check_didactum_sensors_humidity(item, params, parsed):
    if item in parsed["humidity"]:
        return check_humidity(parsed["humidity"][item]["value"], params)


def check_didactum_sensors_voltage(item, params, parsed):
    if item in parsed["voltage"]:
        data = parsed["voltage"][item]
        return check_elphase(
            item,
            params,
            {item: {"voltage": (data["value"], (data["state"], data["state_readable"]))}},
        )
