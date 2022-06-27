#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.base.plugins.agent_based.hr_mem as hr_mem


@pytest.mark.parametrize(
    "string_table,expected_parsed_data",
    [
        (
            [
                [
                    [".1.3.6.1.2.1.25.2.1.2", "Physical memory", "4096", "11956593", "11597830"],
                    [".1.3.6.1.2.1.25.2.1.2", "Real memory", "4096", "181626", "381"],
                    [".1.3.6.1.2.1.25.2.1.3", "Virtual memory", "4096", "807034", "1604"],
                    [".1.3.6.1.2.1.25.2.1.1", "Memory buffers", "1024", "115200", "49683"],
                    [".1.3.6.1.2.1.25.2.1.1", "Cached memory", "4096", "6806420", "232624"],
                    [".1.3.6.1.2.1.25.2.1.1", "Shared virtual memory", "4096", "29817", "1598"],
                    [".1.3.6.1.2.1.25.2.1.1", "Shared real memory", "4096", "27356", "377"],
                    [".1.3.6.1.2.1.25.2.1.3", "Swap space", "4096", "0", "0"],
                    [".1.3.6.1.2.1.25.3.9.3", "", "10", "10", "10"],
                    [".1.3.6.1.2.1.25.3.9.1", "", "30", "1", "1"],
                    [".1.3.6.1.2.1.25.3.9.7", "", "40", "4", "4"],
                    [".1.3.6.1.2.1.25.3.9.3", "", "asdf", "af", "cceu"],
                ]
            ],
            {
                "RAM": [
                    ("physical memory", 48974204928, 47504711680),
                    ("real memory", 743940096, 1560576),
                ],
                "other": [
                    ("memory buffers", 117964800, 50875392),
                    ("cached memory", 27879096320, 952827904),
                    ("shared virtual memory", 122130432, 6545408),
                    ("shared real memory", 112050176, 1544192),
                ],
                "virtual memory": [
                    ("virtual memory", 3305611264, 6569984),
                    ("swap space", 0, 0),
                ],
            },
        ),
        (
            [
                [
                    [
                        ".1.3.6.1.2.1.25.2.1.2",
                        "Physical memory",
                        "4096 Bytes",
                        "11956593",
                        "11597830",
                    ],
                    [".1.3.6.1.2.1.25.2.1.2", "Real memory", "4096 Bytes", "181626", "381"],
                    [".1.3.6.1.2.1.25.2.1.3", "Virtual memory", "4096 Bytes", "807034", "1604"],
                    [".1.3.6.1.2.1.25.2.1.1", "Memory buffers", "1024 Bytes", "115200", "49683"],
                    [".1.3.6.1.2.1.25.2.1.1", "Cached memory", "4096 Bytes", "6806420", "232624"],
                    [
                        ".1.3.6.1.2.1.25.2.1.1",
                        "Shared virtual memory",
                        "4096 Bytes",
                        "29817",
                        "1598",
                    ],
                    [".1.3.6.1.2.1.25.2.1.1", "Shared real memory", "4096 Bytes", "27356", "377"],
                    [".1.3.6.1.2.1.25.2.1.3", "Swap space", "4096 Bytes", "0", "0"],
                ]
            ],
            {
                "RAM": [
                    ("physical memory", 48974204928, 47504711680),
                    ("real memory", 743940096, 1560576),
                ],
                "other": [
                    ("memory buffers", 117964800, 50875392),
                    ("cached memory", 27879096320, 952827904),
                    ("shared virtual memory", 122130432, 6545408),
                    ("shared real memory", 112050176, 1544192),
                ],
                "virtual memory": [
                    ("virtual memory", 3305611264, 6569984),
                    ("swap space", 0, 0),
                ],
            },
        ),
        (
            [
                [
                    [".1.3.6.1.2.1.25.2.1.2", "Physical memory", "1024", "16354176", "16064740"],
                    [".1.3.6.1.2.1.25.2.1.3", "Virtual memory", "1024", "49710444", "22074852"],
                    [".1.3.6.1.2.1.25.2.1.1", "Memory buffers", "1024", "16354176", "1879476"],
                    [".1.3.6.1.2.1.25.2.1.1", "Cached memory", "1024", "346124", "346124"],
                    # bad value - don't discover!
                    [".1.3.6.1.2.1.25.2.1.1", "Shared memory", "1024", "0", ""],
                    [".1.3.6.1.2.1.25.2.1.3", "Swap space", "1024", "33356268", "6010112"],
                    [".1.3.6.1.2.1.25.2.1.4", "/mnt/HDA_ROOT", "4096", "126325", "47072"],
                    [".1.3.6.1.2.1.25.2.1.4", "/sys/fs/cgroup/memory", "4096", "0", "0"],
                    [
                        ".1.3.6.1.2.1.25.2.1.4",
                        "/share/CACHE1_DATA",
                        "4096",
                        "130006080",
                        "13741133",
                    ],
                    [
                        ".1.3.6.1.2.1.25.2.1.4",
                        "/share/CACHE2_DATA",
                        "4096",
                        "532605932",
                        "457723044",
                    ],
                    [".1.3.6.1.2.1.25.2.1.4", "/sys/fs/cgroup/cpu", "4096", "0", "0"],
                    [".1.3.6.1.2.1.25.2.1.4", "/mnt/ext", "4096", "106746", "101037"],
                ]
            ],
            {
                "RAM": [
                    ("physical memory", 16746676224, 16450293760),
                ],
                "fixed disk": [
                    ("/mnt/hda_root", 517427200, 192806912),
                    ("/sys/fs/cgroup/memory", 0, 0),
                    ("/share/cache1_data", 532504903680, 56283680768),
                    ("/share/cache2_data", 2181553897472, 1874833588224),
                    ("/sys/fs/cgroup/cpu", 0, 0),
                    ("/mnt/ext", 437231616, 413847552),
                ],
                "other": [
                    ("memory buffers", 16746676224, 1924583424),
                    ("cached memory", 354430976, 354430976),
                ],
                "virtual memory": [
                    ("virtual memory", 50903494656, 22604648448),
                    ("swap space", 34156818432, 6154354688),
                ],
            },
        ),
        (
            [
                [
                    ["", "Swap space", "1024", "6143996", "144128"],
                    ["", "/", "4096", "125957388", "7714723"],
                ]
            ],
            {},
        ),
    ],
)
def test_hr_mem(string_table, expected_parsed_data) -> None:
    assert hr_mem.pre_parse_hr_mem(string_table) == expected_parsed_data


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just run this file from your IDE and dive into the code.
    import os

    from tests.testlib.utils import cmk_path

    assert not pytest.main(
        ["--doctest-modules", os.path.join(cmk_path(), "cmk/base/plugins/agent_based/hr_mem.py")]
    )
    pytest.main(["-T=unit", "-vvsx", __file__])
