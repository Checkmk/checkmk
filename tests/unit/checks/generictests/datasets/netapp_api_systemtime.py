#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off

from typing import Any

checkname = "netapp_api_systemtime"

info = [["FAS8020-2", "1498108660", "1498108660"]]

discovery: dict[str, list[tuple[str, dict[Any, Any]]]] = {"": [("FAS8020-2", {})]}

checks: dict[
    str,
    list[
        tuple[str, dict[Any, Any], list[tuple[int, str, list[tuple[str, int, Any, Any, Any, Any]]]]]
    ],
] = {
    "": [
        (
            "FAS8020-2",
            {},
            [
                (0, "System time: 2017-06-22 07:17:40", []),
                (0, "Time difference: 0 seconds", [("time_difference", 0, None, None, None, None)]),
            ],
        )
    ]
}
