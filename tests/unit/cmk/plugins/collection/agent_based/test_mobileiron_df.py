#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import StringTable
from cmk.plugins.collection.agent_based.mobileiron_section import parse_mobileiron_df
from cmk.plugins.lib.df import BlocksSubsection, DfBlock, InodesSubsection


@pytest.mark.parametrize(
    "json_raw, expected_results",
    [
        (
            [[r'{"totalCapacity": 44, "availableCapacity": 22}']],
            (
                [
                    DfBlock(
                        device="/root",
                        fs_type=None,
                        size_mb=45056,
                        avail_mb=22528,
                        reserved_mb=0.0,
                        mountpoint="/",
                        uuid=None,
                    ),
                ],
                [],
            ),
        ),
        (
            [[r'{"totalCapacity": 0, "availableCapacity": 0}']],
            (
                [
                    DfBlock(
                        device="/root",
                        fs_type=None,
                        size_mb=0,
                        avail_mb=0,
                        reserved_mb=0.0,
                        mountpoint="/",
                        uuid=None,
                    ),
                ],
                [],
            ),
        ),
    ],
)
def test_parse_mobileiron_df(
    json_raw: StringTable, expected_results: tuple[BlocksSubsection, InodesSubsection]
) -> None:
    assert parse_mobileiron_df(json_raw) == expected_results
