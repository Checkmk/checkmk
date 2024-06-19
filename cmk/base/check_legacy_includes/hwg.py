#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


map_units = {"1": "c", "2": "f", "3": "k", "4": "%"}

map_dev_states = {
    "0": "invalid",
    "1": "normal",
    "2": "out of range low",
    "3": "out of range high",
    "4": "alarm low",
    "5": "alarm high",
}


def parse_hwg(info):
    parsed: dict[str, dict] = {}

    for index, descr, sensorstatus, current, unit in info:
        # Parse Humidity
        if int(sensorstatus) != 0 and map_units.get(unit, "") == "%":
            parsed.setdefault(
                index,
                {
                    "descr": descr,
                    "humidity": float(current),
                    "dev_status_name": map_dev_states.get(sensorstatus, "n.a."),
                    "dev_status": sensorstatus,
                },
            )

        # Parse Temperature
        else:
            try:
                tempval: float | None = float(current)
            except ValueError:
                tempval = None

            parsed.setdefault(
                index,
                {
                    "descr": descr,
                    "dev_unit": map_units.get(unit),
                    "temperature": tempval,
                    "dev_status_name": map_dev_states.get(sensorstatus, ""),
                    "dev_status": sensorstatus,
                },
            )

    return parsed
