#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "ups_eaton_enviroment"


info = [
    ["1", "40", "3"],
]


discovery = {
    "": [
        (None, {}),
    ],
}


checks = {
    "": [
        (
            None,
            {"humidity": (65, 80), "remote_temp": (40, 50), "temp": (40, 50)},
            [
                (
                    1,
                    "Temperature: 1 °C (warn/crit at 40 °C/50 °C),"
                    " Remote-Temperature: 40 °C (warn/crit at 40 °C/50 °C)(!),"
                    " Humidity: 3% (warn/crit at 65%/80%)",
                    [
                        ("temp", 1, 40, 50, None, None),
                        ("remote_temp", 40, 40, 50, None, None),
                        ("humidity", 3, 65, 80, None, None),
                    ],
                ),
            ],
        ),
    ],
}
