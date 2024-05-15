#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.liebert.agent_based.lib import parse_liebert


def test_parse_liebert() -> None:
    assert parse_liebert(
        [
            [
                [
                    "Supply Fluid Temp Set Point 1",
                    "14.0",
                    "deg C",
                    "Supply Fluid Temp Set Point 2",
                    "-6",
                    "deg C",
                    "Supply Fluid Over Temp Alarm Threshold",
                    "0",
                    "deg C",
                    "Supply Fluid Under Temp Warning Threshold",
                    "0",
                    "deg C",
                    "Supply Fluid Under Temp Alarm Threshold",
                    "0",
                    "deg C",
                    "Supply Fluid Over Temp Warning Threshold",
                    "32",
                    "deg F",
                ]
            ]
        ],
        float,
    ) == {
        "Supply Fluid Over Temp Alarm Threshold": (0.0, "deg C"),
        "Supply Fluid Over Temp Warning Threshold": (32.0, "deg F"),
        "Supply Fluid Temp Set Point 1": (14.0, "deg C"),
        "Supply Fluid Temp Set Point 2": (-6.0, "deg C"),
        "Supply Fluid Under Temp Alarm Threshold": (0.0, "deg C"),
        "Supply Fluid Under Temp Warning Threshold": (0.0, "deg C"),
    }
