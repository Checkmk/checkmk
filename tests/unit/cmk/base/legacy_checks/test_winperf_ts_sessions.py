#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable, Mapping
from typing import Any

from pytest import mark, param

from cmk.base.legacy_checks.winperf_ts_sessions import (
    check_winperf_ts_sessions,
    inventory_winperf_ts_sessions,
)

from cmk.agent_based.v2 import StringTable

_SECTION = [[1385714515.93, 2102], [2, 20, "rawcount"], [4, 18, "rawcount"], [6, 2, "rawcount"]]
_NEW_SECTION = [[1385714515.93, 2102], [4, 18, "rawcount"], [6, 2, "rawcount"], [2, 20, "rawcount"]]
_PERFDATA = [("active", 18), ("inactive", 2)]


@mark.parametrize("section, expected", [[_SECTION, [(None, {})]], [[], []]])
def test_inventory_winperf_ts_sessions(
    section: StringTable, expected: Iterable[tuple[str | None, Mapping[str, Any]]]
) -> None:
    assert list(inventory_winperf_ts_sessions(section)) == expected


@mark.parametrize(
    "section,params,expected",
    [
        param(_SECTION, {}, (0, "18 Active, 2 Inactive", _PERFDATA)),
        param(_SECTION, {"active": (10, 20)}, (1, "18 Active(!), 2 Inactive", _PERFDATA)),
        param(_SECTION, {"inactive": (1, 20)}, (1, "18 Active, 2 Inactive(!)", _PERFDATA)),
        param(_NEW_SECTION, {}, (0, "18 Active, 2 Inactive", _PERFDATA)),
        param(_NEW_SECTION, {"active": (10, 20)}, (1, "18 Active(!), 2 Inactive", _PERFDATA)),
        param(_NEW_SECTION, {"inactive": (1, 20)}, (1, "18 Active, 2 Inactive(!)", _PERFDATA)),
    ],
)
def test_check_winperf_ts_sessions(section, params, expected):
    assert check_winperf_ts_sessions(None, params, section) == expected
