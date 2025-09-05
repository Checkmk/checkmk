#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.plugins.collection.agent_based.kernel import parse_kernel

# fmt: off

freeze_time = "2020-06-04 15:40:00"

mock_item_state = {
    "performance": (0, 0),
    "util": {"cpu.util.core.high.cpu0": 1591285080, "cpu.util.core.high.cpu1": 1591285080},
}

checkname = "kernel"

parsed = parse_kernel(
    [
        ["11238"],
        ["nr_free_pages", "198749"],
        ["pgpgin", "169984814"],
        ["pgpgout", "97137765"],
        ["pswpin", "250829"],
        ["pswpout", "751706"],
        ["pgmajfault", "1795031"],
        ["cpu", "13008772", "12250", "5234590", "181918601", "73242", "0", "524563", "0", "0", "0"],
        ["cpu0", "1602366", "1467", "675813", "22730303", "9216", "0", "265437", "0", "0", "0"],
        ["cpu1", "1463624", "1624", "576516", "22975174", "8376", "0", "116908", "0", "0", "0"],
        ["ctxt", "539210403"],
        ["processes", "4700038"],
    ]
)

discovery: Mapping[str, Sequence[tuple[str | None, Mapping[object, object]]]] = {
    "": [],
    "performance": [(None, {})],
}

_basic_result_util = [
    (0, "User: 6.49%", [("user", 6.48547647710549)]),
    (0, "System: 2.87%", [("system", 2.868503817100648)]),
    (0, "Wait: 0.04%", [("wait", 0.03648018320959447)]),
    (0, "Total CPU: 9.39%", [("util", 9.390460477415733, None, None, 0, None)]),
]

checks = {
    "": [],
    "performance": [
        (
            None,
            {},
            [
                (
                    0,
                    "Process Creations: 418.23/s",
                    [("process_creations", 418.2272646378359, None, None, 0.0, None)],
                ),
                (
                    0,
                    "Context Switches: 47980.99/s",
                    [("context_switches", 47980.99332621463, None, None, 0.0, None)],
                ),
                (
                    0,
                    "Major Page Faults: 159.73/s",
                    [("major_page_faults", 159.72868837871508, None, None, 0.0, None)],
                ),
                (
                    0,
                    "Page Swap in: 22.32/s",
                    [("page_swap_in", 22.319718811176365, None, None, 0.0, None)],
                ),
                (
                    0,
                    "Page Swap Out: 66.89/s",
                    [("page_swap_out", 66.8896600818651, None, None, 0.0, None)],
                ),
            ],
        ),
        (
            None,
            {
                "ctxt": (30000.0, 45000.0),
                "processes": (400.0, 500.0),
                "page_swap_in_levels": (10.0, 50.0),
                "page_swap_out_levels_lower": (500.0, 100.0),
            },
            [
                (
                    1,
                    "Process Creations: 418.23/s (warn/crit at 400.00/s/500.00/s)",
                    [("process_creations", 418.2272646378359, 400.0, 500.0, 0.0)],
                ),
                (
                    2,
                    "Context Switches: 47980.99/s (warn/crit at 30000.00/s/45000.00/s)",
                    [("context_switches", 47980.99332621463, 30000.0, 45000.0, 0.0)],
                ),
                (
                    0,
                    "Major Page Faults: 159.73/s",
                    [("major_page_faults", 159.72868837871508, None, None, 0.0, None)],
                ),
                (
                    1,
                    "Page Swap in: 22.32/s (warn/crit at 10.00/s/50.00/s)",
                    [("page_swap_in", 22.319718811176365, 10.0, 50.0, 0.0, None)],
                ),
                (
                    2,
                    "Page Swap Out: 66.89/s (warn/crit below 500.00/s/100.00/s)",
                    [("page_swap_out", 66.8896600818651, None, None, 0.0, None)],
                ),
            ],
        ),
    ],
}
