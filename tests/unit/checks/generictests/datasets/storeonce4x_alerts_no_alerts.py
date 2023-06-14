#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "storeonce4x_alerts"
info = [
    [
        '{"count": 100, "total": 232, "unFilteredTotal": 0, "start": 0, "prevPageUri": "/rest/alerts?start=0&count=100&category=alerts", "nextPageUri": "/rest/alerts?start=100&count=100&category=alerts", "category": "resources", "members": []}'
    ]
]

discovery = {"": [(None, {})]}

checks = {
    "": [
        (
            None,
            {},
            [
                (0, "No alerts at all found", []),
            ],
        )
    ]
}
