#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore


checkname = "splunk_alerts"


info = [["5"]]


discovery = {"": [(None, {})]}


checks = {
    "": [
        (
            None,
            {},
            [(0, "Number of fired alerts: 5", [("fired_alerts", 5, None, None, None, None)])],
        )
    ]
}
