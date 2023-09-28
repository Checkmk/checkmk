#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "alcatel_timetra_cpu"

info = [["92"]]

discovery = {"": [(None, {})]}

checks = {
    "": [
        (
            None,
            (90.0, 95.0),
            [
                (
                    1,
                    "Total CPU: 92.00% (warn/crit at 90.00%/95.00%)",
                    [("util", 92, 90.0, 95.0, 0, 100)],
                )
            ],
        )
    ]
}
