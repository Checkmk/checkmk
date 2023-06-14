#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "elasticsearch_nodes"


info = [
    ["DGfRL2s", "open_file_descriptors", "462"],
    ["DGfRL2s", "max_file_descriptors", "4096"],
    ["DGfRL2s", "cpu_percent", "0"],
    ["DGfRL2s", "cpu_total_in_millis", "157950"],
    ["DGfRL2s", "mem_total_virtual_in_bytes", "7135776768"],
    ["fKw8YbK", "open_file_descriptors", "442"],
    ["fKw8YbK", "max_file_descriptors", "4096"],
    ["fKw8YbK", "cpu_percent", "0"],
    ["fKw8YbK", "cpu_total_in_millis", "94820"],
    ["fKw8YbK", "mem_total_virtual_in_bytes", "7106904064"],
    ["ZwGy2o7", "open_file_descriptors", "453"],
    ["ZwGy2o7", "max_file_descriptors", "4096"],
    ["ZwGy2o7", "cpu_percent", "0"],
    ["ZwGy2o7", "cpu_total_in_millis", "97700"],
    ["ZwGy2o7", "mem_total_virtual_in_bytes", "7123750912"],
    ["huh3AiI", "open_file_descriptors", "453"],
    ["huh3AiI", "max_file_descriptors", "4096"],
    ["huh3AiI", "cpu_percent", "0"],
    ["huh3AiI", "cpu_total_in_millis", "96740"],
    ["huh3AiI", "mem_total_virtual_in_bytes", "7106514944"],
    ["g8YT0-P", "open_file_descriptors", "447"],
    ["g8YT0-P", "max_file_descriptors", "4096"],
    ["g8YT0-P", "cpu_percent", "0"],
    ["g8YT0-P", "cpu_total_in_millis", "104530"],
    ["g8YT0-P", "mem_total_virtual_in_bytes", "7122513920"],
]


discovery = {
    "": [("DGfRL2s", {}), ("ZwGy2o7", {}), ("fKw8YbK", {}), ("g8YT0-P", {}), ("huh3AiI", {})]
}


checks = {
    "": [
        (
            "DGfRL2s",
            {"cpu_levels": (75.0, 90.0)},
            [
                (0, "CPU used: 0%", [("cpu_percent", 0.0, 75.0, 90.0, None, None)]),
                (
                    0,
                    "CPU total in ms: 157950",
                    [("cpu_total_in_millis", 157950, None, None, None, None)],
                ),
                (
                    0,
                    "Total virtual memory: 6.65 GiB",
                    [("mem_total_virtual_in_bytes", 7135776768, None, None, None, None)],
                ),
                (
                    0,
                    "Open file descriptors: 462",
                    [("open_file_descriptors", 462, None, None, None, None)],
                ),
                (
                    0,
                    "Max file descriptors: 4096",
                    [("max_file_descriptors", 4096, None, None, None, None)],
                ),
            ],
        ),
        (
            "ZwGy2o7",
            {"cpu_levels": (75.0, 90.0)},
            [
                (0, "CPU used: 0%", [("cpu_percent", 0.0, 75.0, 90.0, None, None)]),
                (
                    0,
                    "CPU total in ms: 97700",
                    [("cpu_total_in_millis", 97700, None, None, None, None)],
                ),
                (
                    0,
                    "Total virtual memory: 6.63 GiB",
                    [("mem_total_virtual_in_bytes", 7123750912, None, None, None, None)],
                ),
                (
                    0,
                    "Open file descriptors: 453",
                    [("open_file_descriptors", 453, None, None, None, None)],
                ),
                (
                    0,
                    "Max file descriptors: 4096",
                    [("max_file_descriptors", 4096, None, None, None, None)],
                ),
            ],
        ),
        (
            "fKw8YbK",
            {"cpu_levels": (75.0, 90.0)},
            [
                (0, "CPU used: 0%", [("cpu_percent", 0.0, 75.0, 90.0, None, None)]),
                (
                    0,
                    "CPU total in ms: 94820",
                    [("cpu_total_in_millis", 94820, None, None, None, None)],
                ),
                (
                    0,
                    "Total virtual memory: 6.62 GiB",
                    [("mem_total_virtual_in_bytes", 7106904064, None, None, None, None)],
                ),
                (
                    0,
                    "Open file descriptors: 442",
                    [("open_file_descriptors", 442, None, None, None, None)],
                ),
                (
                    0,
                    "Max file descriptors: 4096",
                    [("max_file_descriptors", 4096, None, None, None, None)],
                ),
            ],
        ),
        (
            "g8YT0-P",
            {"cpu_levels": (75.0, 90.0)},
            [
                (0, "CPU used: 0%", [("cpu_percent", 0.0, 75.0, 90.0, None, None)]),
                (
                    0,
                    "CPU total in ms: 104530",
                    [("cpu_total_in_millis", 104530, None, None, None, None)],
                ),
                (
                    0,
                    "Total virtual memory: 6.63 GiB",
                    [("mem_total_virtual_in_bytes", 7122513920, None, None, None, None)],
                ),
                (
                    0,
                    "Open file descriptors: 447",
                    [("open_file_descriptors", 447, None, None, None, None)],
                ),
                (
                    0,
                    "Max file descriptors: 4096",
                    [("max_file_descriptors", 4096, None, None, None, None)],
                ),
            ],
        ),
        (
            "huh3AiI",
            {"cpu_levels": (75.0, 90.0)},
            [
                (0, "CPU used: 0%", [("cpu_percent", 0.0, 75.0, 90.0, None, None)]),
                (
                    0,
                    "CPU total in ms: 96740",
                    [("cpu_total_in_millis", 96740, None, None, None, None)],
                ),
                (
                    0,
                    "Total virtual memory: 6.62 GiB",
                    [("mem_total_virtual_in_bytes", 7106514944, None, None, None, None)],
                ),
                (
                    0,
                    "Open file descriptors: 453",
                    [("open_file_descriptors", 453, None, None, None, None)],
                ),
                (
                    0,
                    "Max file descriptors: 4096",
                    [("max_file_descriptors", 4096, None, None, None, None)],
                ),
            ],
        ),
    ]
}
