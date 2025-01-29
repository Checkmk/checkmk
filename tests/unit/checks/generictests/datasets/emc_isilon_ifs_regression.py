#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.collection.agent_based.emc_isilon_ifs import parse_emc_isilon_ifs

# fmt: off
# mypy: disable-error-code=var-annotated
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_LEVELS

checkname = "emc_isilon_ifs"

parsed = parse_emc_isilon_ifs([["615553001652224", "599743491129344"]])

discovery = {"": [("Cluster", None)]}

checks = {
    "": [
        (
            "Cluster",
            FILESYSTEM_DEFAULT_LEVELS,
            [
                (
                    0,
                    "Used: 2.57% - 14.4 TiB of 560 TiB",
                    [
                        ("fs_used", 15077125, 469629670.4, 528333379.2, 0, 587037088.0),
                        ("fs_free", 571959963, None, None, 0, None),
                        ("fs_used_percent", 2.5683428369691015, 80.0, 90.0, 0.0, 100.0),
                        ("fs_size", 587037088, None, None, 0, None),
                    ],
                )
            ],
        )
    ]
}
