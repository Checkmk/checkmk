#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.mobileiron_section import parse_mobileiron_df
from cmk.base.plugins.agent_based.utils.df import BlocksSubsection, DfBlock, InodesSubsection


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
