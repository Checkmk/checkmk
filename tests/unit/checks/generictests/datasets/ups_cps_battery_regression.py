#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "ups_cps_battery"


info = [["73", "41", "528000"]]


discovery = {"": [(None, {})], "temp": [("Battery", {})]}


checks = {
    "": [
        (
            None,
            {"capacity": (95, 90)},
            [
                (2, "Capacity at 73% (warn/crit at 95/90%)", []),
                (0, "88 minutes remaining on battery", []),
            ],
        )
    ],
    "temp": [("Battery", {}, [(0, "41 \xb0C", [("temp", 41, None, None, None, None)])])],
}
