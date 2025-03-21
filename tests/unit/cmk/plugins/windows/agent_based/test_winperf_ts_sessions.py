#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import Any

from pytest import mark, param

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.windows.agent_based.winperf_ts_sessions import (
    check_winperf_ts_sessions,
    discovery_winperf_ts_sessions,
)

# Note: The order of columns was changed in Windows. For more details, see comment in plugin code.
_SECTION = [[1385714515.93, 2102], [2, 20, "rawcount"], [4, 18, "rawcount"], [6, 2, "rawcount"]]
_NEW_SECTION = [[1385714515.93, 2102], [4, 18, "rawcount"], [6, 2, "rawcount"], [2, 20, "rawcount"]]

METRIC_ACTIVE_OK = Metric(name="active", value=18)
METRIC_ACTIVE_WARN = Metric(name="active", value=18, levels=(10.0, 20.0))
METRIC_INACTIVE_OK = Metric(name="inactive", value=2)
METRIC_INACTIVE_WARN = Metric(name="inactive", value=2, levels=(1.0, 20.0))

RESULT_ACTIVE_OK = Result(state=State.OK, summary="18 Active")
RESULT_ACTIVE_WARN = Result(
    state=State.WARN, summary="18 Active (warn/crit at 10 Active/20 Active)"
)
RESULT_INACTIVE_OK = Result(state=State.OK, summary="2 Inactive")
RESULT_INACTIVE_WARN = Result(
    state=State.WARN, summary="2 Inactive (warn/crit at 1 Inactive/20 Inactive)"
)
_PERFDATA = [Metric("active", 18), Metric("inactive", 2)]


@mark.parametrize("section, expected", [[_SECTION, [Service()]], [[], []]])
def test_discovery_winperf_ts_sessions(section: StringTable, expected: DiscoveryResult) -> None:
    assert list(discovery_winperf_ts_sessions(section)) == expected


@mark.parametrize(
    "section,params,expected",
    [
        param(
            _SECTION,
            {},
            [RESULT_ACTIVE_OK, METRIC_ACTIVE_OK, RESULT_INACTIVE_OK, METRIC_INACTIVE_OK],
            id="all ok (old column order)",
        ),
        param(
            _SECTION,
            {"active": ("fixed", (10, 20))},
            [RESULT_ACTIVE_WARN, METRIC_ACTIVE_WARN, RESULT_INACTIVE_OK, METRIC_INACTIVE_OK],
            id="number of active sessions exceeds warn threshold (old column order)",
        ),
        param(
            _SECTION,
            {"inactive": ("fixed", (1, 20))},
            [RESULT_ACTIVE_OK, METRIC_ACTIVE_OK, RESULT_INACTIVE_WARN, METRIC_INACTIVE_WARN],
            id="number of inactive sessions exceeds warn threshold (old column order)",
        ),
        param(
            _SECTION,
            {"active": ("fixed", (10, 20)), "inactive": ("fixed", (1, 20))},
            [RESULT_ACTIVE_WARN, METRIC_ACTIVE_WARN, RESULT_INACTIVE_WARN, METRIC_INACTIVE_WARN],
            id="both warn thresholds exceeded (old column order)",
        ),
        param(
            _NEW_SECTION,
            {},
            [RESULT_ACTIVE_OK, METRIC_ACTIVE_OK, RESULT_INACTIVE_OK, METRIC_INACTIVE_OK],
            id="all ok (new column order)",
        ),
        param(
            _NEW_SECTION,
            {"active": ("fixed", (10, 20))},
            [RESULT_ACTIVE_WARN, METRIC_ACTIVE_WARN, RESULT_INACTIVE_OK, METRIC_INACTIVE_OK],
            id="number of active sessions exceeds warn threshold (new column order)",
        ),
        param(
            _NEW_SECTION,
            {"inactive": ("fixed", (1, 20))},
            [RESULT_ACTIVE_OK, METRIC_ACTIVE_OK, RESULT_INACTIVE_WARN, METRIC_INACTIVE_WARN],
            id="number of inactive sessions exceeds warn threshold (new column order)",
        ),
        param(
            _NEW_SECTION,
            {"active": ("fixed", (10, 20)), "inactive": ("fixed", (1, 20))},
            [RESULT_ACTIVE_WARN, METRIC_ACTIVE_WARN, RESULT_INACTIVE_WARN, METRIC_INACTIVE_WARN],
            id="both warn thresholds exceeded (new column order)",
        ),
    ],
)
def test_check_winperf_ts_sessions(
    section: StringTable, params: Mapping[str, Any], expected: CheckResult
) -> None:
    assert list(check_winperf_ts_sessions(params, section)) == expected
