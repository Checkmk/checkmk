#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "alcatel_temp_aos7"

info = [["45", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0"]]

discovery = {"": [("CPMA", {})]}

checks = {
    "": [
        (
            "CPMA",
            {"levels": (45, 50)},
            [(1, "45 \xb0C (warn/crit at 45/50 \xb0C)", [("temp", 45, 45, 50, None, None)])],
        )
    ]
}
