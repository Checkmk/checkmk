#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.mem_used_sections import (
    parse_openbsd_mem,
    parse_solaris_mem,
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
    [
        (
            [
                ["MemTotal:", "23", "B"],
                ["MemFree:", "744076", "kB"],
                ["SwapFree:", "186505", "kB"],
            ]
        )
    ],
)
def test_parse_openbsd_mem_error(string_table: StringTable) -> None:
    with pytest.raises(KeyError):
        parse_openbsd_mem(string_table)


def _solaris_mem(memory_line: str) -> StringTable:
    """Build a <<<solaris_mem>>> section from a `top` "Memory:" line (as the agent ships it)."""
    return [memory_line.split()]


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        pytest.param(
            _solaris_mem("Memory: 10G phys mem, 1905M free mem, 8002M total swap, 8002M free swap"),
            {
                "MemTotal": 10 * 1024**3,
                "MemFree": 1905 * 1024**2,
                "SwapTotal": 8002 * 1024**2,
                "SwapFree": 8002 * 1024**2,
            },
            id="variant A (phys mem/total swap), all fields",
        ),
        pytest.param(
            # `top` prints only non-zero values, so free swap == 0 drops the last field
            _solaris_mem("Memory: 512M phys mem, 353M free mem, 2000M total swap"),
            {
                "MemTotal": 512 * 1024**2,
                "MemFree": 353 * 1024**2,
                "SwapTotal": 2000 * 1024**2,
                "SwapFree": 0,
            },
            id="variant A, free swap omitted",
        ),
        pytest.param(
            # ... and `top` may leave a dangling "," behind when it drops the field
            _solaris_mem("Memory: 512M phys mem, 353M free mem, 2000M total swap,"),
            {
                "MemTotal": 512 * 1024**2,
                "MemFree": 353 * 1024**2,
                "SwapTotal": 2000 * 1024**2,
                "SwapFree": 0,
            },
            id="variant A, free swap omitted with trailing comma",
        ),
        pytest.param(
            # an omitted *inner* field must not shift the remaining values
            _solaris_mem("Memory: 64G phys mem, 4096M total swap, 8K free swap"),
            {
                "MemTotal": 64 * 1024**3,
                "MemFree": 0,
                "SwapTotal": 4096 * 1024**2,
                "SwapFree": 8 * 1024,
            },
            id="variant A, free mem omitted",
        ),
        pytest.param(
            # no swap configured -> both swap fields drop out
            _solaris_mem("Memory: 64G phys mem, 4972M free mem"),
            {
                "MemTotal": 64 * 1024**3,
                "MemFree": 4972 * 1024**2,
                "SwapTotal": 0,
                "SwapFree": 0,
            },
            id="variant A, no swap",
        ),
        pytest.param(
            _solaris_mem("Memory: 256G real, 54G free, 257G swap in use, 86G swap free"),
            {
                "MemTotal": 256 * 1024**3,
                "MemFree": 54 * 1024**3,
                "SwapTotal": (257 + 86) * 1024**3,  # in use + free
                "SwapFree": 86 * 1024**3,
            },
            id="variant B (real/swap in use), all fields",
        ),
        pytest.param(
            # swap in use == 0 (configured but unused) drops the inner field; SwapFree
            # must stay correct rather than being read as 0 (previously misreported)
            _solaris_mem("Memory: 2048M real, 913M free, 2863M swap free"),
            {
                "MemTotal": 2048 * 1024**2,
                "MemFree": 913 * 1024**2,
                "SwapTotal": 2863 * 1024**2,
                "SwapFree": 2863 * 1024**2,
            },
            id="variant B, swap in use omitted",
        ),
        pytest.param(
            [],
            None,
            id="empty section",
        ),
    ],
)
def test_parse_solaris_mem(
    string_table: StringTable,
    expected_result: SectionMemUsed | None,
) -> None:
    result = parse_solaris_mem(string_table)
    assert result == expected_result
