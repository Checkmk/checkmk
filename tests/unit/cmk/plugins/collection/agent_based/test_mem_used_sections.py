#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import StringTable
from cmk.plugins.collection.agent_based.mem_used_sections import (
    parse_freebsd_mem,
    parse_openbsd_mem,
)
from cmk.plugins.lib.memory import SectionMemUsed


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        (
            [
                ["MemTotal:", "1032116", "kB"],
                ["MemFree:", "744076", "kB"],
                ["SwapTotal:", "186505", "kB"],
                ["SwapFree:", "186505", "kB"],
            ],
            {
                "MemFree": 744076 * 1024,
                "MemTotal": 1032116 * 1024,
                "SwapFree": 186505 * 1024,
                "SwapTotal": 186505 * 1024,
            },
        ),
        pytest.param(
            [
                ["MemTotal:", "1032116", "kB"],
                ["MemFree:", "8125", "MB"],
                ["SwapTotal:", "186505", "kB"],
                ["SwapFree:", "186505", "kB"],
            ],
            {
                "MemFree": 8125 * 1024**2,
                "MemTotal": 1032116 * 1024,
                "SwapFree": 186505 * 1024,
                "SwapTotal": 186505 * 1024,
            },
            id="MemFree in MB",
        ),
        (
            [
                ["MemTotal:", "1032116", "kB"],
                ["MemTotal2:", "1032116", "kB"],
                ["MemFree:", "744076", "kB"],
                ["SwapTotal:", "186505", "kB"],
                ["SwapFree:", "186505", "kB"],
            ],
            None,
        ),
        (
            [
                ["MemTotal:", "1032116", "kB"],
                ["MemFree:", "744076", "kB"],
                ["SwapFree:", "186505", "kB"],
            ],
            None,
        ),
        (
            [
                ["MemTotal:", "aa", "kB"],
                ["MemFree:", "744076", "kB"],
                ["SwapFree:", "186505", "kB"],
            ],
            None,
        ),
    ],
)
def test_parse_openbsd_mem(
    string_table: StringTable,
    expected_result: SectionMemUsed | None,
) -> None:
    result = parse_openbsd_mem(string_table)
    assert result == expected_result


@pytest.mark.parametrize(
    "string_table",
    [([["MemTotal:", "23", "B"], ["MemFree:", "744076", "kB"], ["SwapFree:", "186505", "kB"]])],
)
def test_parse_openbsd_mem_error(string_table: StringTable) -> None:
    with pytest.raises(KeyError):
        parse_openbsd_mem(string_table)


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        pytest.param(
            [
                ["vm.stats.vm.v_page_size:", "4096"],
                ["vm.stats.vm.v_cache_count:", "0"],
                ["vm.stats.vm.v_free_count:", "1400469"],
                ["vm.kmem_size:", "16567554048"],
                ["vm.swap_total:", "4172431360"],
                ["swap.used", "0"],
            ],
            {
                "MemFree": 5736321024,
                "MemTotal": 16567554048,
                "SwapFree": 4172431360,
                "SwapTotal": 4172431360,
                "Cached": 0,
            },
            id="With trailing colon",
        ),
        pytest.param(
            [
                ["vm.stats.vm.v_page_size", "4096"],
                ["vm.stats.vm.v_cache_count", "0"],
                ["vm.stats.vm.v_free_count", "1400469"],
                ["vm.kmem_size", "16567554048"],
                ["vm.swap_total", "4172431360"],
                ["swap.used", "0"],
            ],
            {
                "MemFree": 5736321024,
                "MemTotal": 16567554048,
                "SwapFree": 4172431360,
                "SwapTotal": 4172431360,
                "Cached": 0,
            },
            id="W/o trailing colon",
        ),
        pytest.param(
            [
                ["vm.stats.vm.v_page_size:", "4096"],
                ["vm.stats.vm.v_cache_count:", "0"],
                ["vm.kmem_size:", "16567554048"],
                ["vm.swap_total:", "4172431360"],
                ["swap.used", "0"],
            ],
            None,
            id="Missing v_free_count",
        ),
    ],
)
def test_parse_freebsd_mem(
    string_table: StringTable,
    expected_result: SectionMemUsed | None,
) -> None:
    result = parse_freebsd_mem(string_table)
    assert result == expected_result
