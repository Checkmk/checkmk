#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import StringTable
from cmk.plugins.cisco_sma.agent_based.df import _parse_df
from cmk.plugins.lib.df import DfBlock


def test_parse_df() -> None:
    assert _parse_df(
        [
            [
                "Total_disk_space: 198.391 GB, Available_disk_space: 157.752 GB, Used_disk_space: 40.639 GB, Used_disk_space in % : 20.48"
            ]
        ]
    ) == (
        [
            DfBlock(
                device="",
                fs_type=None,
                size_mb=198.391 * 10**3,
                avail_mb=157.752 * 10**3,
                reserved_mb=40.639 * 10**3,
                mountpoint="/",
                uuid=None,
            )
        ],
        [],
    )


@pytest.mark.parametrize("inp", (([]), ([[]])))
def test_parsing_empty_input(inp: StringTable) -> None:
    assert _parse_df(inp) is None
