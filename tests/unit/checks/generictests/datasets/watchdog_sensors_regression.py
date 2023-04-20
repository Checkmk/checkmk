#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off


checkname = "watchdog_sensors"


info = [
    [["3.2.0", "1"]],
    [
        ["1", "First Floor Ambient", "1", "213", "37", "60", ""],
        ["2", "Second Floor Ambient", "1", "200", "30", "40", ""],
    ],
]


discovery: dict[str, object] = {
    "": [("Watchdog 1", {}), ("Watchdog 2", {})],
    "dew": [("Dew point 1", {}), ("Dew point 2", {})],
    "humidity": [("Humidity 1", {}), ("Humidity 2", {})],
    "temp": [("Temperature 1", {}), ("Temperature 2", {})],
}


checks = {
    "": [
        ("Watchdog 1", {}, [(0, "available", []), (0, "Location: First Floor Ambient", [])]),
        ("Watchdog 2", {}, [(0, "available", []), (0, "Location: Second Floor Ambient", [])]),
    ],
    "dew": [
        ("Dew point 1", {}, [(0, "6.0 \xb0C", [("temp", 6.0, None, None, None, None)])]),
        ("Dew point 2", {}, [(0, "4.0 \xb0C", [("temp", 4.0, None, None, None, None)])]),
    ],
    "humidity": [
        (
            "Humidity 1",
            {"levels": (50, 55), "levels_lower": (10, 15)},
            [(0, "37.0%", [("humidity", 37, 50, 55, None, None)])],
        ),
        (
            "Humidity 2",
            {"levels": (50, 55), "levels_lower": (10, 15)},
            [(0, "30.0%", [("humidity", 30, 50, 55, None, None)])],
        ),
    ],
    "temp": [
        ("Temperature 1", {}, [(0, "21.3 \xb0C", [("temp", 21.3, None, None, None, None)])]),
        ("Temperature 2", {}, [(0, "20.0 \xb0C", [("temp", 20.0, None, None, None, None)])]),
    ],
}
