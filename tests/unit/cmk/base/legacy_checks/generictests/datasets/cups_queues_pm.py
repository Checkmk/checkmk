#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "cups_queues"

info = [
    ["printer", "spr1", "is", "idle.", "enabled", "since", "Thu", "Mar", "11", "14:28:23", "2010"],
    [
        "printer",
        "lpr2",
        "now",
        "printing",
        "lpr2-3.",
        "enabled",
        "since",
        "Tue",
        "Jun",
        "29",
        "09:22:04",
        "2010",
    ],
    [
        "Wiederherstellbar:",
        "Der",
        "Netzwerk-Host",
        "lpr2",
        "ist",
        "beschaeftigt,",
        "erneuter",
        "Versuch",
        "in",
        "30",
        "Sekunden",
    ],
    ["---"],
    ["lpr2-2", "root", "1024", "Tue", "28", "Jun", "2010", "01:02:35", "PM", "CET"],
    ["lpr2-3", "root", "1024", "Tue", "29", "Jun", "2010", "09:05:54", "AM", "CET"],
    ["lpr2-4", "root", "1024", "Tue", "Jun", "29", "09:05:56", "2010"],
]

discovery = {"": [("lpr2", {}), ("spr1", {})]}

checks = {
    "": [
        (
            "lpr2",
            {
                "disabled_since": 2,
                "is_idle": 0,
                "job_age": (360, 720),
                "job_count": (5, 10),
                "now_printing": 0,
            },
            [
                (
                    0,
                    "now printing lpr2-3. enabled since Tue Jun 29 09:22:04 2010 (Wiederherstellbar: Der Netzwerk-Host lpr2 ist beschaeftigt, erneuter Versuch in 30 Sekunden)",
                    [],
                ),
                (0, "Jobs: 3", [("jobs", 3, 5, 10, 0, None)]),
                (2, "Oldest job is from Mon Jun 28 14:02:35 2010", []),
            ],
        ),
        (
            "spr1",
            {
                "disabled_since": 2,
                "is_idle": 0,
                "job_age": (360, 720),
                "job_count": (5, 10),
                "now_printing": 0,
            },
            [(0, "is idle. enabled since Thu Mar 11 14:28:23 2010", [])],
        ),
    ]
}
