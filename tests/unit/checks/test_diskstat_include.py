#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

import pytest

import cmk.base.check_legacy_includes.diskstat
from cmk.base.check_legacy_includes.diskstat import check_diskstat_line

from .checktestlib import assertCheckResultsEqual, CheckResult

pytestmark = pytest.mark.checks


def get_rate(_vs, _counter, _time, value, raise_overflow):
    return value


def get_average(__store, counter, _time, value, _time_span):
    return round(value / 10.0) * 10.0


@pytest.mark.parametrize(
    "args,expected_result",
    [
        (
            (1, "", {}, [None, None, 101, 201]),
            CheckResult(
                (
                    0,
                    "read: 51.7 kB/s, write: 103 kB/s",
                    [
                        ("read", 51712),
                        ("write", 102912),
                    ],
                )
            ),
        ),
        (
            (1, "", {"average": 1}, [None, None, 101, 201]),
            CheckResult(
                (
                    0,
                    "read: 51.7 kB/s, write: 103 kB/s",
                    [
                        ("read", 51712),
                        ("write", 102912),
                        ("read.avg", 51710.0),
                        ("write.avg", 102910.0),
                    ],
                )
            ),
        ),
    ],
)
def test_check_diskstat_line(
    monkeypatch: pytest.MonkeyPatch,
    args: tuple[float, str, Mapping[str, object], Sequence[object]],
    expected_result: CheckResult,
    initialised_item_state: None,
) -> None:
    monkeypatch.setattr(cmk.base.check_legacy_includes.diskstat, "get_rate", get_rate)
    monkeypatch.setattr(cmk.base.check_legacy_includes.diskstat, "get_average", get_average)
    actual_result = CheckResult(check_diskstat_line(*args))
    assertCheckResultsEqual(actual_result, expected_result)
