#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.ibm.agent_based.ibm_svc_host import (
    _HostParams,
    check_ibm_svc_host,
    discover_ibm_svc_host,
    parse_ibm_svc_host,
)

_STRING_TABLE: StringTable = [
    ["0", "h_esx01", "2", "4", "degraded"],
    ["1", "host206", "2", "2", "online"],
    ["2", "host105", "2", "2", "online"],
    ["3", "host106", "2", "2", "online"],
]

# 7 online hosts + 3 offline hosts — used to test offline thresholds
_STRING_TABLE_WITH_OFFLINE: StringTable = [
    ["0", "host1", "2", "2", "online"],
    ["1", "host2", "2", "2", "online"],
    ["2", "host3", "2", "2", "online"],
    ["3", "host4", "2", "2", "online"],
    ["4", "host5", "2", "2", "online"],
    ["5", "host6", "2", "2", "online"],
    ["6", "host7", "2", "2", "online"],
    ["7", "host8", "2", "2", "offline"],
    ["8", "host9", "2", "2", "offline"],
    ["9", "host10", "2", "2", "offline"],
]


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (_STRING_TABLE, [Service()]),
        ([], []),
    ],
)
def test_discover_ibm_svc_host(
    string_table: StringTable, expected_discoveries: list[Service]
) -> None:
    parsed = parse_ibm_svc_host(string_table)
    assert list(discover_ibm_svc_host(parsed)) == expected_discoveries


@pytest.mark.parametrize(
    "params, string_table, expected_results",
    [
        # No levels configured — all OK
        (
            {},
            _STRING_TABLE,
            [
                Result(state=State.OK, summary="Active: 3"),
                Metric("active", 3.0),
                Result(state=State.OK, summary="Inactive: 0"),
                Metric("inactive", 0.0),
                Result(state=State.OK, summary="Degraded: 1"),
                Metric("degraded", 1.0),
                Result(state=State.OK, summary="Offline: 0"),
                Metric("offline", 0.0),
                Result(state=State.OK, summary="Other: 0"),
                Metric("other", 0.0),
            ],
        ),
        # always_ok=False: degraded host triggers WARN
        (
            {"always_ok": False},
            [
                ["0", "h_esx01", "2", "4", "degraded"],
                ["1", "host206", "2", "2", "online"],
            ],
            [
                Result(state=State.OK, summary="1 active, 0 inactive"),
                Metric("active", 1.0),
                Metric("inactive", 0.0),
                Metric("degraded", 1.0),
                Metric("offline", 0.0),
                Metric("other", 0.0),
                Result(state=State.WARN, summary="1 degraded"),
            ],
        ),
        # always_ok=True: degraded host, but state forced to OK
        (
            {"always_ok": True},
            [
                ["0", "h_esx01", "2", "4", "degraded"],
                ["1", "host206", "2", "2", "online"],
            ],
            [
                Result(state=State.OK, summary="1 active, 0 inactive"),
                Metric("active", 1.0),
                Metric("inactive", 0.0),
                Metric("degraded", 1.0),
                Metric("offline", 0.0),
                Metric("other", 0.0),
                Result(state=State.OK, summary="1 degraded"),
            ],
        ),
        # inactive_hosts warn level: inactive count at warn threshold
        (
            {"inactive_hosts": (1, 5)},
            [
                ["0", "h_esx01", "2", "4", "inactive"],
                ["1", "host206", "2", "2", "online"],
            ],
            [
                Result(state=State.OK, summary="Active: 1"),
                Metric("active", 1.0),
                Result(state=State.WARN, summary="Inactive: 1 (warn/crit at 1/5)"),
                Metric("inactive", 1.0, levels=(1.0, 5.0)),
                Result(state=State.OK, summary="Degraded: 0"),
                Metric("degraded", 0.0),
                Result(state=State.OK, summary="Offline: 0"),
                Metric("offline", 0.0),
                Result(state=State.OK, summary="Other: 0"),
                Metric("other", 0.0),
            ],
        ),
        # active_hosts warn level: active count below warn threshold
        (
            {"active_hosts": (5, 2)},
            [
                ["0", "host206", "2", "2", "online"],
                ["1", "host207", "2", "2", "online"],
                ["2", "host208", "2", "2", "online"],
            ],
            [
                Result(state=State.WARN, summary="Active: 3 (warn/crit below 5/2)"),
                Metric("active", 3.0),
                Result(state=State.OK, summary="Inactive: 0"),
                Metric("inactive", 0.0),
                Result(state=State.OK, summary="Degraded: 0"),
                Metric("degraded", 0.0),
                Result(state=State.OK, summary="Offline: 0"),
                Metric("offline", 0.0),
                Result(state=State.OK, summary="Other: 0"),
                Metric("other", 0.0),
            ],
        ),
        # offline_hosts warn level: offline count exceeds warn but not crit
        (
            {"offline_hosts": (2, 5)},
            _STRING_TABLE_WITH_OFFLINE,
            [
                Result(state=State.OK, summary="Active: 7"),
                Metric("active", 7.0),
                Result(state=State.OK, summary="Inactive: 0"),
                Metric("inactive", 0.0),
                Result(state=State.OK, summary="Degraded: 0"),
                Metric("degraded", 0.0),
                Result(state=State.WARN, summary="Offline: 3 (warn/crit at 2/5)"),
                Metric("offline", 3.0, levels=(2.0, 5.0)),
                Result(state=State.OK, summary="Other: 0"),
                Metric("other", 0.0),
            ],
        ),
        # offline_crit_takes_priority_over_warn: crit=3 matches offline count — must yield CRIT, not WARN
        (
            {"offline_hosts": (2, 3)},
            _STRING_TABLE_WITH_OFFLINE,
            [
                Result(state=State.OK, summary="Active: 7"),
                Metric("active", 7.0),
                Result(state=State.OK, summary="Inactive: 0"),
                Metric("inactive", 0.0),
                Result(state=State.OK, summary="Degraded: 0"),
                Metric("degraded", 0.0),
                Result(state=State.CRIT, summary="Offline: 3 (warn/crit at 2/3)"),
                Metric("offline", 3.0, levels=(2.0, 3.0)),
                Result(state=State.OK, summary="Other: 0"),
                Metric("other", 0.0),
            ],
        ),
    ],
)
def test_check_ibm_svc_host(
    params: _HostParams,
    string_table: StringTable,
    expected_results: list[Result | Metric],
) -> None:
    parsed = parse_ibm_svc_host(string_table)
    assert list(check_ibm_svc_host(params, parsed)) == expected_results
