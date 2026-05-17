#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.db2.agent_based.db2_logsizes import (
    _check_db2_logsizes,
    discover_db2_logsizes,
    parse_db2_logsizes,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                ["[[[db2mpss:ASMPROD]]]"],
                ["TIMESTAMP", "1474466290"],
                ["usedspace", "2204620"],
                ["logfilsiz", "2000"],
                ["logprimary", "5"],
                ["logsecond", "20"],
            ],
            [Service(item="db2mpss:ASMPROD")],
        ),
    ],
)
def test_discover_db2_logsizes(
    string_table: StringTable,
    expected_discoveries: Sequence[Service],
) -> None:
    """Test discovery function for db2_logsizes check."""
    parsed = parse_db2_logsizes(string_table)
    result = list(discover_db2_logsizes(parsed))
    assert result == list(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "db2mpss:ASMPROD",
            {"levels": (-20.0, -10.0)},
            [
                ["[[[db2mpss:ASMPROD]]]"],
                ["TIMESTAMP", "1474466290"],
                ["usedspace", "-"],
                ["logfilsiz", "2000"],
                ["logprimary", "5"],
                ["logsecond", "20"],
            ],
            [Result(state=State.UNKNOWN, summary="Can not read usedspace")],
        ),
        (
            "db2mpss:ASMPROD",
            {"levels": (-20.0, -10.0)},
            [
                ["[[[db2mpss:ASMPROD]]]"],
                ["TIMESTAMP", "1474466290"],
                ["usedspace", "2204620"],
                ["logfilsiz", "2000"],
                ["logprimary", "5"],
                ["logsecond", "20"],
            ],
            [
                Metric("fs_used", 2.0, levels=(156.0, 175.5), boundaries=(0.0, 195.0)),
                Metric("fs_free", 193.0, boundaries=(0.0, None)),
                Metric(
                    "fs_used_percent",
                    1.0256410256410255,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(state=State.OK, summary="Used: 1.03% - 2.00 MiB of 195 MiB"),
                Metric("fs_size", 195, boundaries=(0, None)),
            ],
        ),
    ],
)
def test_check_db2_logsizes(
    item: str,
    params: Mapping[str, tuple[float, float]],
    string_table: StringTable,
    expected_results: Sequence[Result | Metric],
) -> None:
    """Test check function for db2_logsizes check."""
    parsed = parse_db2_logsizes(string_table)
    result = list(_check_db2_logsizes({}, item, params, parsed))
    assert result == list(expected_results)
