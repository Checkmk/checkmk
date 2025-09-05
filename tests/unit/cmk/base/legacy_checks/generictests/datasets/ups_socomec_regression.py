#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "ups_socomec_in_voltage"


info = [["1", "2300"]]


discovery = {"": [("1", {})]}


checks = {
    "": [
        (
            "1",
            {"levels_lower": (210, 180)},
            [
                (
                    0,
                    "in voltage: 230V, (warn/crit at 210V/180V)",
                    [("in_voltage", 230, 210, 180, 150, None)],
                )
            ],
        )
    ]
}
