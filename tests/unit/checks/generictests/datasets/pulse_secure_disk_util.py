#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "pulse_secure_disk_util"

info = [["7"]]

discovery = {"": [(None, {})]}

checks = {
    "": [
        (
            None,
            {"upper_levels": (80.0, 90.0)},
            [
                (
                    0,
                    "Percentage of disk space used: 7.00%",
                    [("disk_utilization", 7, 80.0, 90.0, None, None)],
                )
            ],
        )
    ]
}
