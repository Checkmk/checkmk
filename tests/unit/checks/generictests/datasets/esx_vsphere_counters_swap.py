#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

from cmk.plugins.vsphere.agent_based.esx_vsphere_counters import parse_esx_vsphere_counters

checkname = "esx_vsphere_counters_swap"

parsed = parse_esx_vsphere_counters(
    [
        ["mem.swapin", "", "0", "kiloBytes"],
        ["mem.swapout", "", "", "kiloBytes"],
        ["mem.swapused", "", "0", "kiloBytes"],
    ]
)

discovery = {
    "": [(None, {})]
}

checks = {
    "": [
        (
            None,
            {},
            [
                (0, "Swap in: 0 B", []),
                (0, "Swap out: not available", []),
                (0, "Swap used: 0 B", []),
            ],
        )
    ]
}
