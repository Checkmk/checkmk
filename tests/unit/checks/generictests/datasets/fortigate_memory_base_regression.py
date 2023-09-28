#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "fortigate_memory_base"


info = [
    ["19", "1887424"],
]


discovery = {
    "": [(None, {})],
}


checks = {
    "": [
        (
            None,
            (70, 80),
            [
                (
                    0,
                    "Used: 19.00% - 350 MiB of 1.80 GiB",
                    [
                        (
                            "mem_used",
                            367217213.44,
                            1352905523.1999998,
                            1546177740.8000002,
                            0,
                            1932722176,
                        ),
                    ],
                ),
            ],
        ),
        (
            None,
            {"levels": (15.0, 85.0)},
            [
                (
                    1,
                    "Used: 19.00% - 350 MiB of 1.80 GiB (warn/crit at 15.00%/85.00% used)",
                    [("mem_used", 367217213.44, 289908326.4, 1642813849.6, 0, 1932722176)],
                ),
            ],
        ),
        (
            None,
            {"levels": (-85.0, -15.0)},
            [
                (
                    1,
                    "Used: 19.00% - 350 MiB of 1.80 GiB (warn/crit below 85.00%/15.00% free)",
                    [
                        ("mem_used", 367217213.44, 289908326.4000001, 1642813849.6, 0, 1932722176),
                    ],
                ),
            ],
        ),
        (
            None,
            {"levels": (340, 1500)},
            [
                (
                    1,
                    "Used: 19.00% - 350 MiB of 1.80 GiB (warn/crit at 340 MiB/1.46 GiB used)",
                    [
                        ("mem_used", 367217213.44, 356515840.0, 1572864000.0, 0, 1932722176),
                    ],
                ),
            ],
        ),
        (
            None,
            {"levels": (-1717, -1)},
            [
                (
                    1,
                    "Used: 19.00% - 350 MiB of 1.80 GiB (warn/crit below 1.68 GiB/1.00 MiB free)",
                    [
                        ("mem_used", 367217213.44, 132317184.0, 1931673600.0, 0, 1932722176),
                    ],
                ),
            ],
        ),
    ],
}
