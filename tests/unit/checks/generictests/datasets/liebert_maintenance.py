#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "liebert_maintenance"


info = [["Calculated Next Maintenance Month", "9"], ["Calculated Next Maintenance Year", "2019"]]


freeze_time = "2019-08-23T12:00:00"

discovery = {"": [(None, {})]}


checks = {
    "": [
        (
            None,
            {"levels": (10, 5)},
            [
                (0, "Next maintenance: 9/2019", []),
                (1, "7 days 11 hours (warn/crit below 10 days 0 hours/5 days 0 hours)", []),
            ],
        ),
    ],
}
