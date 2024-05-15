#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "juniper_screenos_mem"


info = [["157756272", "541531248"]]


discovery = {"": [(None, {})]}


checks = {
    "": [
        (
            None,
            {"levels": ("perc_used", (80.0, 90.0))},
            [
                (
                    0,
                    "Used: 22.56% - 150 MiB of 667 MiB",
                    [('mem_used', 157756272, 559430016.0, 629358768.0, 0, 699287520)],
                )
            ],
        )
    ]
}
