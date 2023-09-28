#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "openhardwaremonitor"


info = [
    ["Index", "Name", "Parent", "SensorType", "Value"],
    ["0", "Temperature", "/hdd/0", "Temperature", "28.000000"],
    ["0", "System Fan", "/lpc/w83627dhgp", "Fan", "1506.696411"],
    ["1", "CPU Fan", "/lpc/w83627dhgp", "Fan", "2518.656738"],
    ["1", "CPU Cores", "/intelcpu/0", "Power", "1.651155"],
    ["0", "CPU Core #1", "/intelcpu/0", "Temperature", "28.000000"],
    ["0", "Remaining Life", "/hdd/0", "Level", "98.000000"],
    ["1", "CPU Core #1", "/intelcpu/0", "Clock", "1297.013062"],
    ["1", "CPU Core #1", "/intelcpu/0", "Load", "12.307692"],
    ["2", "CPU Core #2", "/intelcpu/0", "Clock", "1297.013062"],
    ["0", "Memory", "/ram", "Load", "61.928921"],
    ["2", "CPU Graphics", "/intelcpu/0", "Power", "0.040867"],
    ["1", "CPU Core #2", "/intelcpu/0", "Temperature", "29.000000"],
    ["3", "CPU DRAM", "/intelcpu/0", "Power", "1.188020"],
    ["2", "CPU Core #3", "/intelcpu/0", "Temperature", "31.000000"],
    ["1", "Host Writes to Controller", "/hdd/0", "Data", "1589.000000"],
    ["2", "Host Reads", "/hdd/0", "Data", "1366.000000"],
    ["4", "CPU Core #4", "/intelcpu/0", "Load", "6.153846"],
    ["3", "CPU Core #3", "/intelcpu/0", "Clock", "1297.013062"],
    ["3", "CPU Core #3", "/intelcpu/0", "Load", "18.461536"],
    ["4", "CPU Core #4", "/intelcpu/0", "Clock", "1297.013062"],
    ["1", "Available Memory", "/ram", "Data", "3.011536"],
    ["2", "CPU Core #2", "/intelcpu/0", "Load", "15.384615"],
    ["0", "Controller Writes to NAND", "/hdd/0", "Data", "3371.000000"],
    ["1", "Write Amplification", "/hdd/0", "Factor", "2.121460"],
    ["0", "CPU Total", "/intelcpu/0", "Load", "13.076920"],
    ["0", "Bus Speed", "/intelcpu/0", "Clock", "99.770233"],
    ["0", "Used Memory", "/ram", "Data", "4.898762"],
    ["3", "CPU Core #4", "/intelcpu/0", "Temperature", "27.000000"],
    ["4", "CPU Package", "/intelcpu/0", "Temperature", "31.000000"],
    ["0", "Used Space", "/hdd/0", "Load", "72.429222"],
]


discovery = {
    "": [
        ("cpu0 Bus Speed", {}),
        ("cpu0 Core #1", {}),
        ("cpu0 Core #2", {}),
        ("cpu0 Core #3", {}),
        ("cpu0 Core #4", {}),
    ],
    "fan": [("lpcw83627dhgp Fan", {}), ("lpcw83627dhgp System Fan", {})],
    "power": [("cpu0 Cores", {}), ("cpu0 DRAM", {}), ("cpu0 Graphics", {})],
    "smart": [("hdd0", {})],
    "temperature": [
        ("cpu0 Core #1", {}),
        ("cpu0 Core #2", {}),
        ("cpu0 Core #3", {}),
        ("cpu0 Core #4", {}),
        ("cpu0 Package", {}),
        ("hdd0", {}),
    ],
}


checks = {
    "": [
        ("cpu0 Bus Speed", {}, [(0, "99.8 MHz", [("clock", 99.770233, None, None, None, None)])]),
        ("cpu0 Core #1", {}, [(0, "1297.0 MHz", [("clock", 1297.013062, None, None, None, None)])]),
        ("cpu0 Core #2", {}, [(0, "1297.0 MHz", [("clock", 1297.013062, None, None, None, None)])]),
        ("cpu0 Core #3", {}, [(0, "1297.0 MHz", [("clock", 1297.013062, None, None, None, None)])]),
        ("cpu0 Core #4", {}, [(0, "1297.0 MHz", [("clock", 1297.013062, None, None, None, None)])]),
    ],
    "fan": [
        (
            "lpcw83627dhgp Fan",
            {"lower": (None, None), "upper": (None, None)},
            [(0, "Speed: 2518 RPM", [])],
        ),
        (
            "lpcw83627dhgp System Fan",
            {"lower": (None, None), "upper": (None, None)},
            [(0, "Speed: 1506 RPM", [])],
        ),
    ],
    "power": [
        ("cpu0 Cores", {}, [(0, "1.7 W", [("w", 1.651155, None, None, None, None)])]),
        ("cpu0 DRAM", {}, [(0, "1.2 W", [("w", 1.18802, None, None, None, None)])]),
        ("cpu0 Graphics", {}, [(0, "0.0 W", [("w", 0.040867, None, None, None, None)])]),
    ],
    "smart": [
        (
            "hdd0",
            {"remaining_life": (30, 10)},
            [(0, "Remaining Life 98.0%", [("remaining_life", 98.0, None, None, None, None)])],
        )
    ],
    "temperature": [
        (
            "cpu0 Core #1",
            {
                "_default": {"levels": (70, 80)},
                "cpu": {"levels": (60, 70)},
                "hdd": {"levels": (40, 50)},
            },
            [(0, "28.0 \xb0C", [("temp", 28.0, 60, 70, None, None)])],
        ),
        (
            "cpu0 Core #2",
            {
                "_default": {"levels": (70, 80)},
                "cpu": {"levels": (60, 70)},
                "hdd": {"levels": (40, 50)},
            },
            [(0, "29.0 \xb0C", [("temp", 29.0, 60, 70, None, None)])],
        ),
        (
            "cpu0 Core #3",
            {
                "_default": {"levels": (70, 80)},
                "cpu": {"levels": (60, 70)},
                "hdd": {"levels": (40, 50)},
            },
            [(0, "31.0 \xb0C", [("temp", 31.0, 60, 70, None, None)])],
        ),
        (
            "cpu0 Core #4",
            {
                "_default": {"levels": (70, 80)},
                "cpu": {"levels": (60, 70)},
                "hdd": {"levels": (40, 50)},
            },
            [(0, "27.0 \xb0C", [("temp", 27.0, 60, 70, None, None)])],
        ),
        (
            "cpu0 Package",
            {
                "_default": {"levels": (70, 80)},
                "cpu": {"levels": (60, 70)},
                "hdd": {"levels": (40, 50)},
            },
            [(0, "31.0 \xb0C", [("temp", 31.0, 60, 70, None, None)])],
        ),
        (
            "hdd0",
            {
                "_default": {"levels": (70, 80)},
                "cpu": {"levels": (60, 70)},
                "hdd": {"levels": (40, 50)},
            },
            [(0, "28.0 \xb0C", [("temp", 28.0, 40, 50, None, None)])],
        ),
    ],
}
