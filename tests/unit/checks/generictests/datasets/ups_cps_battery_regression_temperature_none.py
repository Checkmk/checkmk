#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "ups_cps_battery"


info = [["100", "NULL", "612000"]]


discovery = {"": [(None, {})]}


checks = {
    "": [
        (
            None,
            {"capacity": (95, 90)},
            [
                (0, "Capacity at 100%", []),
                (0, "102 minutes remaining on battery", []),
            ],
        )
    ],
    "temp": [("Battery", {}, [])],
}
