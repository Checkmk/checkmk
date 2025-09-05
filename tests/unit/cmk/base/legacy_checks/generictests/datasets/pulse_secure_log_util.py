#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "pulse_secure_log_util"

info = [["19"]]

discovery = {"": [(None, {})]}

checks = {
    "": [
        (
            None,
            {},
            [
                (
                    0,
                    "Percentage of log file used: 19.00%",
                    [("log_file_utilization", 19, None, None, None, None)],
                )
            ],
        )
    ]
}
