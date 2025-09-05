#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "ddn_s2a_statsdelay"

info = [
    [
        "0@106@time_interval_in_seconds@0.1@host_reads@696778332@host_writes@171313693@disk_reads@96732186@disk_writes@2717578@time_interval_in_seconds@0.2@host_reads@128302@host_writes@19510@disk_reads@120584@disk_writes@40175@time_interval_in_seconds@0.3@host_reads@10803@host_writes@5428@disk_reads@7028@disk_writes@1645@time_interval_in_seconds@0.4@host_reads@2662@host_writes@2846@disk_reads@1687@disk_writes@270@time_interval_in_seconds@0.5@host_reads@71@host_writes@1588@disk_reads@48@disk_writes@10@time_interval_in_seconds@0.6@host_reads@22@host_writes@925@disk_reads@17@disk_writes@2@time_interval_in_seconds@0.7@host_reads@33@host_writes@611@disk_reads@9@disk_writes@0@time_interval_in_seconds@0.8@host_reads@4@host_writes@331@disk_reads@3@disk_writes@0@time_interval_in_seconds@0.9@host_reads@5@host_writes@249@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.0@host_reads@0@host_writes@116@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.1@host_reads@0@host_writes@52@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.2@host_reads@0@host_writes@19@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.3@host_reads@0@host_writes@20@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.4@host_reads@0@host_writes@14@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.5@host_reads@0@host_writes@11@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.6@host_reads@0@host_writes@1@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.7@host_reads@0@host_writes@0@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.8@host_reads@0@host_writes@1@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.9@host_reads@0@host_writes@0@disk_reads@0@disk_writes@0@time_interval_in_seconds@2.0@host_reads@0@host_writes@0@disk_reads@0@disk_writes@0@additional_intervals@1@time_interval_in_seconds@>10.0@host_reads@0@host_writes@3@disk_reads@0@disk_writes@0@$"
    ],
    ["OVER"],
]

discovery = {"": [("Disk", {}), ("Host", {})]}

checks = {
    "": [
        (
            "Disk",
            {"read_avg": (0.1, 0.2), "write_avg": (0.1, 0.2)},
            [
                (
                    1,
                    "Average read wait: 0.10 s (warn/crit at 0.10/0.20 s)",
                    [("disk_average_read_wait", 0.10015052916930892, 0.1, 0.2, None, None)],
                ),
                (
                    0,
                    "Min. read wait: 0.10 s",
                    [("disk_min_read_wait", 0.1, None, None, None, None)],
                ),
                (
                    0,
                    "Max. read wait: 0.80 s",
                    [("disk_max_read_wait", 0.8, None, None, None, None)],
                ),
                (
                    1,
                    "Average write wait: 0.10 s (warn/crit at 0.10/0.20 s)",
                    [("disk_average_write_wait", 0.10307514405550547, 0.1, 0.2, None, None)],
                ),
                (
                    0,
                    "Min. write wait: 0.10 s",
                    [("disk_min_write_wait", 0.1, None, None, None, None)],
                ),
                (
                    0,
                    "Max. write wait: 0.60 s",
                    [("disk_max_write_wait", 0.6, None, None, None, None)],
                ),
            ],
        ),
        (
            "Host",
            {"read_avg": (0.1, 0.2), "write_avg": (0.1, 0.2)},
            [
                (
                    1,
                    "Average read wait: 0.10 s (warn/crit at 0.10/0.20 s)",
                    [("disk_average_read_wait", 0.10000550296888959, 0.1, 0.2, None, None)],
                ),
                (
                    0,
                    "Min. read wait: 0.10 s",
                    [("disk_min_read_wait", 0.1, None, None, None, None)],
                ),
                (
                    0,
                    "Max. read wait: 0.90 s",
                    [("disk_max_read_wait", 0.9, None, None, None, None)],
                ),
                (
                    1,
                    "Average write wait: 0.10 s (warn/crit at 0.10/0.20 s)",
                    [("disk_average_write_wait", 0.10001182480424102, 0.1, 0.2, None, None)],
                ),
                (
                    0,
                    "Min. write wait: 0.10 s",
                    [("disk_min_write_wait", 0.1, None, None, None, None)],
                ),
                (
                    0,
                    "Max. write wait: 30.00 s",
                    [("disk_max_write_wait", 30, None, None, None, None)],
                ),
            ],
        ),
    ]
}

mock_item_state = {
    "": {
        "time_intervals": [
            0.1,
            0.2,
            0.3,
            0.4,
            0.5,
            0.6,
            0.7,
            0.8,
            0.9,
            1.0,
            1.1,
            1.2,
            1.3,
            1.4,
            1.5,
            1.6,
            1.7,
            1.8,
            1.9,
            2.0,
            30,
        ],
        "reads": [86732186, 110584, 6028, 687, 45, 13, 6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "writes": [2617578, 39175, 645, 230, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    }
}
