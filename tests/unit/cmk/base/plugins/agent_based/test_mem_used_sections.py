#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.mem_used_sections import parse_openbsd_mem
from cmk.base.plugins.agent_based.utils.memory import SectionMemUsed


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
    expected_result: Optional[SectionMemUsed],
) -> None:
    result = parse_openbsd_mem(string_table)
    assert result == expected_result


@pytest.mark.parametrize(
    "string_table",
    [([["MemTotal:", "23", "B"], ["MemFree:", "744076", "kB"], ["SwapFree:", "186505", "kB"]])],
)
def test_parse_openbsd_mem_error(string_table):
    with pytest.raises(KeyError):
        parse_openbsd_mem(string_table)
