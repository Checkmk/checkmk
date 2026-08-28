#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.legacy_checks.fortigate_memory_base import (
    check_fortigate_memory_base,
    discover_fortigate_memory_base,
    parse_fortigate_memory_base,
)

_SECTION = (367217213.44, 1932722176.0)


@pytest.mark.parametrize(
    "string_table, expected",
    [
        ([["19", "1887424"]], _SECTION),
        ([], None),
        ([["19", "not a number"]], None),
    ],
)
def test_parse_fortigate_memory_base(
    string_table: StringTable, expected: tuple[float, float] | None
) -> None:
    assert parse_fortigate_memory_base(string_table) == expected


def test_discover_fortigate_memory_base() -> None:
    assert list(discover_fortigate_memory_base(_SECTION)) == [Service()]


@pytest.mark.parametrize(
    "params, expected_results",
    [
        (
            (70, 80),
            [
                Result(state=State.OK, summary="Used: 19.00% - 350 MiB of 1.80 GiB"),
                Metric(
                    "mem_used",
                    367217213.44,
                    levels=(1352905523.1999998, 1546177740.8000002),
                    boundaries=(0.0, 1932722176.0),
                ),
            ],
        ),
        (
            {"levels": (15.0, 85.0)},
            [
                Result(
                    state=State.WARN,
                    summary="Used: 19.00% - 350 MiB of 1.80 GiB (warn/crit at 15.00%/85.00% used)",
                ),
                Metric(
                    "mem_used",
                    367217213.44,
                    levels=(289908326.4, 1642813849.6),
                    boundaries=(0.0, 1932722176.0),
                ),
            ],
        ),
        (
            {"levels": (-85.0, -15.0)},
            [
                Result(
                    state=State.WARN,
                    summary=(
                        "Used: 19.00% - 350 MiB of 1.80 GiB (warn/crit below 85.00%/15.00% free)"
                    ),
                ),
                Metric(
                    "mem_used",
                    367217213.44,
                    levels=(289908326.4000001, 1642813849.6),
                    boundaries=(0.0, 1932722176.0),
                ),
            ],
        ),
        (
            {"levels": (340, 1500)},
            [
                Result(
                    state=State.WARN,
                    summary=(
                        "Used: 19.00% - 350 MiB of 1.80 GiB (warn/crit at 340 MiB/1.46 GiB used)"
                    ),
                ),
                Metric(
                    "mem_used",
                    367217213.44,
                    levels=(356515840.0, 1572864000.0),
                    boundaries=(0.0, 1932722176.0),
                ),
            ],
        ),
        (
            {"levels": (-1717, -1)},
            [
                Result(
                    state=State.WARN,
                    summary=(
                        "Used: 19.00% - 350 MiB of 1.80 GiB"
                        " (warn/crit below 1.68 GiB/1.00 MiB free)"
                    ),
                ),
                Metric(
                    "mem_used",
                    367217213.44,
                    levels=(132317184.0, 1931673600.0),
                    boundaries=(0.0, 1932722176.0),
                ),
            ],
        ),
    ],
)
def test_check_fortigate_memory_base(
    params: Mapping[str, object] | tuple[float, float],
    expected_results: Sequence[object],
) -> None:
    assert list(check_fortigate_memory_base(params, _SECTION)) == expected_results
