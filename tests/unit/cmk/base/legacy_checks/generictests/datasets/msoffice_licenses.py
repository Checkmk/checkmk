#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "msoffice_licenses"

info = [
    ["sx:MYLICENSE1", "55", "0", "55"],
    ["sx:MYLICENSE2", "1000000", "0", ""],
    ["sx:MYLICENSE3"],
    ["sx:MYLICENSE4", "130", "0", "120"],
    ["sx:MYLICENSE5", "10000", "0", "1"],
    ["sx:MYLICENSE6", "6575", "0", "6330"],
    ["sx:MYLICENSE7", "3800", "0", "3756"],
    ["sx:MYLICENSE8", "10000", "0", "1424"],
    ["sx:MYLICENSE9", "10000", "0", "4"],
    ["sx:MYLICENSE10", "10000", "0", "5"],
    ["sx:MYLICENSE11", "100", "0", "46"],
    ["sx:MYLICENSE12", "1000000", "0", "194"],
    ["sx:MYLICENSE12", "5925", "0", "1"],
    ["sx:MYLICENSE12", "3600", "0", "5"],
    ["sx:MYLICENSE13", "10665", "0", "10461"],
    ["sx:MYLICENSE13", "840", "0", "803"],
    ["sx:MYLICENSE14", "0", "0", "2"],
    ["sx:MYLICENSE15", "0", "0", "0"],
    ["sx:MYLICENSE16", "5", "1", "4"],
]

discovery = {
    "": [
        ("sx:MYLICENSE1", {}),
        ("sx:MYLICENSE10", {}),
        ("sx:MYLICENSE11", {}),
        ("sx:MYLICENSE12", {}),
        ("sx:MYLICENSE13", {}),
        ("sx:MYLICENSE14", {}),
        ("sx:MYLICENSE15", {}),
        ("sx:MYLICENSE16", {}),
        ("sx:MYLICENSE4", {}),
        ("sx:MYLICENSE5", {}),
        ("sx:MYLICENSE6", {}),
        ("sx:MYLICENSE7", {}),
        ("sx:MYLICENSE8", {}),
        ("sx:MYLICENSE9", {}),
    ]
}

checks = {
    "": [
        (
            "sx:MYLICENSE1",
            {"usage": (80.0, 90.0)},
            [
                (0, "Consumed licenses: 55", [("licenses", 55, None, None, None, None)]),
                (0, "Active licenses: 55", [("licenses_total", 55, None, None, None, None)]),
                (
                    2,
                    "Usage: 100.00% (warn/crit at 80.00%/90.00%)",
                    [("license_percentage", 100.0, 80.0, 90.0, 0.0, 100.0)],
                ),
            ],
        ),
        (
            "sx:MYLICENSE10",
            {"usage": (80.0, 90.0)},
            [
                (0, "Consumed licenses: 5", [("licenses", 5, None, None, None, None)]),
                (0, "Active licenses: 10000", [("licenses_total", 10000, None, None, None, None)]),
                (0, "Usage: 0.05%", [("license_percentage", 0.05, 80.0, 90.0, 0.0, 100.0)]),
            ],
        ),
        (
            "sx:MYLICENSE11",
            {"usage": (80.0, 90.0)},
            [
                (0, "Consumed licenses: 46", [("licenses", 46, None, None, None, None)]),
                (0, "Active licenses: 100", [("licenses_total", 100, None, None, None, None)]),
                (0, "Usage: 46.00%", [("license_percentage", 46.0, 80.0, 90.0, 0.0, 100.0)]),
            ],
        ),
        (
            "sx:MYLICENSE12",
            {"usage": (80.0, 90.0)},
            [
                (0, "Consumed licenses: 194", [("licenses", 194, None, None, None, None)]),
                (
                    0,
                    "Active licenses: 1000000",
                    [("licenses_total", 1000000, None, None, None, None)],
                ),
                (0, "Usage: 0.02%", [("license_percentage", 0.0194, 80.0, 90.0, 0.0, 100.0)]),
            ],
        ),
        (
            "sx:MYLICENSE13",
            {"usage": (80.0, 90.0)},
            [
                (0, "Consumed licenses: 10461", [("licenses", 10461, None, None, None, None)]),
                (0, "Active licenses: 10665", [("licenses_total", 10665, None, None, None, None)]),
                (
                    2,
                    "Usage: 98.09% (warn/crit at 80.00%/90.00%)",
                    [("license_percentage", 98.08720112517581, 80.0, 90.0, 0.0, 100.0)],
                ),
            ],
        ),
        ("sx:MYLICENSE14", {"usage": (80.0, 90.0)}, [(0, "No active licenses", [])]),
        ("sx:MYLICENSE15", {"usage": (80.0, 90.0)}, [(0, "No active licenses", [])]),
        (
            "sx:MYLICENSE16",
            {"usage": (80.0, 90.0)},
            [
                (0, "Consumed licenses: 4", [("licenses", 4, None, None, None, None)]),
                (0, "Active licenses: 5", [("licenses_total", 5, None, None, None, None)]),
                (
                    1,
                    "Usage: 80.00% (warn/crit at 80.00%/90.00%)",
                    [("license_percentage", 80.0, 80.0, 90.0, 0.0, 100.0)],
                ),
                (0, " Warning units: 1", []),
            ],
        ),
        (
            "sx:MYLICENSE4",
            {"usage": (80.0, 90.0)},
            [
                (0, "Consumed licenses: 120", [("licenses", 120, None, None, None, None)]),
                (0, "Active licenses: 130", [("licenses_total", 130, None, None, None, None)]),
                (
                    2,
                    "Usage: 92.31% (warn/crit at 80.00%/90.00%)",
                    [("license_percentage", 92.3076923076923, 80.0, 90.0, 0.0, 100.0)],
                ),
            ],
        ),
        (
            "sx:MYLICENSE5",
            {"usage": (80.0, 90.0)},
            [
                (0, "Consumed licenses: 1", [("licenses", 1, None, None, None, None)]),
                (0, "Active licenses: 10000", [("licenses_total", 10000, None, None, None, None)]),
                (0, "Usage: 0.01%", [("license_percentage", 0.01, 80.0, 90.0, 0.0, 100.0)]),
            ],
        ),
        (
            "sx:MYLICENSE6",
            {"usage": (80.0, 90.0)},
            [
                (0, "Consumed licenses: 6330", [("licenses", 6330, None, None, None, None)]),
                (0, "Active licenses: 6575", [("licenses_total", 6575, None, None, None, None)]),
                (
                    2,
                    "Usage: 96.27% (warn/crit at 80.00%/90.00%)",
                    [("license_percentage", 96.27376425855513, 80.0, 90.0, 0.0, 100.0)],
                ),
            ],
        ),
        (
            "sx:MYLICENSE7",
            {"usage": (80.0, 90.0)},
            [
                (0, "Consumed licenses: 3756", [("licenses", 3756, None, None, None, None)]),
                (0, "Active licenses: 3800", [("licenses_total", 3800, None, None, None, None)]),
                (
                    2,
                    "Usage: 98.84% (warn/crit at 80.00%/90.00%)",
                    [("license_percentage", 98.84210526315789, 80.0, 90.0, 0.0, 100.0)],
                ),
            ],
        ),
        (
            "sx:MYLICENSE8",
            {"usage": (80.0, 90.0)},
            [
                (0, "Consumed licenses: 1424", [("licenses", 1424, None, None, None, None)]),
                (0, "Active licenses: 10000", [("licenses_total", 10000, None, None, None, None)]),
                (0, "Usage: 14.24%", [("license_percentage", 14.24, 80.0, 90.0, 0.0, 100.0)]),
            ],
        ),
        (
            "sx:MYLICENSE9",
            {"usage": (80.0, 90.0)},
            [
                (0, "Consumed licenses: 4", [("licenses", 4, None, None, None, None)]),
                (0, "Active licenses: 10000", [("licenses_total", 10000, None, None, None, None)]),
                (0, "Usage: 0.04%", [("license_percentage", 0.04, 80.0, 90.0, 0.0, 100.0)]),
            ],
        ),
    ]
}
