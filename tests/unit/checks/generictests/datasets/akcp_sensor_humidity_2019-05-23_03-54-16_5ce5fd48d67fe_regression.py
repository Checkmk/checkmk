#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "akcp_sensor_humidity"


info = [["Humidity1 Description", "", "7", "1"], ["Humidity2 Description", "", "0", "2"]]


discovery = {"": [("Humidity1 Description", (30, 35, 60, 65))]}


checks = {"": [("Humidity1 Description", (30, 35, 60, 65), [(2, "State: sensor error", [])])]}
