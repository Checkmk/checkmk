#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "hitachi_hus_dku"

info = [["210221", "1", "1", "1", "1"]]

discovery = {"": [("210221", None)]}

checks = {
    "": [
        (
            "210221",
            {},
            [
                (0, "Power Supply: no error", []),
                (0, "Fan: no error", []),
                (0, "Environment: no error", []),
                (0, "Drive: no error", []),
            ],
        )
    ]
}
