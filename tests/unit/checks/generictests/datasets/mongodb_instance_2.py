#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code=var-annotated

checkname = "mongodb_instance"

info = [
    ["error", "Instance is down"],
]

discovery = {
    "": [
        (None, None),
    ],
}

checks = {
    "": [
        (
            None,
            {},
            [
                (
                    2,
                    "Instance is down",
                ),
            ],
        ),
    ],
}
