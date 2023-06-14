#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "acme_sbc_snmp"

info = [
    ["20", "2"],
]

discovery = {
    "": [
        (None, {}),
    ],
}

checks = {
    "": [
        (
            None,
            {"levels_lower": (99, 75)},
            [
                (0, "Health state: active", []),
                (2, "Score: 20% (warn/crit at or below 99%/75%)", []),
            ],
        ),
    ],
}
