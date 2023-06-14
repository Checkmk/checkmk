#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "aws_cloudwatch_alarms_limits"

info = [['[["cloudwatch_alarms",', '"TITEL",', "10,", "1,", '"REGION"]]']]

discovery = {"": [("REGION", {})]}

checks = {
    "": [
        (
            "REGION",
            {"cloudwatch_alarms": (None, 80.0, 90.0)},
            [
                (
                    0,
                    "No levels reached",
                    [("aws_cloudwatch_alarms_cloudwatch_alarms", 1, None, None, None, None)],
                ),
                (0, "\nTITEL: 1 (of max. 10)"),
            ],
        )
    ]
}
