#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import StringTable
from cmk.plugins.cisco_sma.agent_based.memory_utilization import _parse_memory_percentage_used


@pytest.mark.parametrize(
    "string_table, expected",
    (
        ([[]], None),
        ([["2"]], 2.0),
    ),
)
def test_parse_memory_percentage_used(string_table: StringTable, expected: None | float) -> None:
    assert _parse_memory_percentage_used(string_table) == expected
