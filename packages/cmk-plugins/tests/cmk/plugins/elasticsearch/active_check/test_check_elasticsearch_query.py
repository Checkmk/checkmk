#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.plugins.elasticsearch.active_check.check_elasticsearch_query import (
    _check_levels,
    _check_lower_levels,
    _check_upper_levels,
)


@pytest.mark.parametrize(
    "value,levels,expected",
    [
        pytest.param(0, (10, 20), (0, ""), id="value < Level"),
        pytest.param(11, (10, 20), (1, "(warn/crit at 10/20)"), id="value > WARN Level"),
        pytest.param(10, (10, 20), (1, "(warn/crit at 10/20)"), id="value == WARN Level"),
        pytest.param(21, (10, 20), (2, "(warn/crit at 10/20)"), id="value > CRIT Level"),
        pytest.param(20, (10, 0), (2, "(warn/crit at 10/0)"), id="CRIT < WARN"),
    ],
)
def test_check_lower_levels(
    value: int,
    levels: tuple[int, int],
    expected: tuple[int, str],
) -> None:
    assert _check_upper_levels(value, levels) == expected


@pytest.mark.parametrize(
    "value,levels,expected",
    [
        pytest.param(21, (20, 10), (0, ""), id="value > Level"),
        pytest.param(20, (20, 10), (0, ""), id="value = Level"),
        pytest.param(15, (20, 10), (1, "(warn/crit below 20/10)"), id="value < WARN Level"),
        pytest.param(5, (20, 10), (2, "(warn/crit below 20/10)"), id="value < CRIT Level"),
        pytest.param(0, (1, 2), (2, "(warn/crit below 1/2)"), id="CRIT before WARN"),
    ],
)
def test_check_upper_levels(
    value: int,
    levels: tuple[int, int],
    expected: tuple[int, str],
) -> None:
    assert _check_lower_levels(value, levels) == expected


@pytest.mark.parametrize(
    "value,uppper_levels,lower_levels,expected",
    [
        pytest.param(5, (10, 20), (2, 1), ("Messages: 5", 0, "count=5"), id="Check OK"),
        pytest.param(
            0,
            (10, 20),
            (2, 1),
            ("Messages: 0 (warn/crit below 2/1)", 2, "count=0"),
            id="Lower level CRIT",
        ),
        pytest.param(
            15,
            (10, 20),
            (2, 1),
            ("Messages: 15 (warn/crit at 10/20)", 1, "count=15"),
            id="Upper level WARN",
        ),
        pytest.param(
            25,
            (10, 20),
            (2, 1),
            ("Messages: 25 (warn/crit at 10/20)", 2, "count=25"),
            id="Upper level CRIT",
        ),
        pytest.param(
            0,
            (0, 0),
            (1, 1),
            ("Messages: 0 (warn/crit at 0/0) (warn/crit below 1/1)", 2, "count=0"),
            id="Level overlap",
        ),
    ],
)
def test_check_levels(
    value: int,
    uppper_levels: tuple[int, int],
    lower_levels: tuple[int, int],
    expected: tuple[str, int, str],
) -> None:
    assert _check_levels(value, "Messages", "count", uppper_levels, lower_levels) == expected
