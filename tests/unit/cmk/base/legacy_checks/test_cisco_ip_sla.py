#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.cisco_ip_sla import (
    check_cisco_ip_sla,
    discover_cisco_ip_sla,
    parse_cisco_ip_sla,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [["6", [10, 96, 66, 4], [10, 96, 27, 69], "1"]],
                [["6", "", "", "9", "5000"]],
                [["6", "6", "", "2", "2", "2"]],
                [["6", "25", "1"]],
            ],
            [("6", {})],
        ),
    ],
)
def test_discover_cisco_ip_sla(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for cisco_ip_sla check."""
    parsed = parse_cisco_ip_sla(string_table)
    result = list(discover_cisco_ip_sla(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "6",
            {
                "completion_time_over_treshold_occured": "no",
                "connection_lost_occured": "no",
                "latest_rtt_completion_time": (250, 500),
                "latest_rtt_state": "ok",
                "state": "active",
                "timeout_occured": "no",
            },
            [
                [["6", [10, 96, 66, 4], [10, 96, 27, 69], "1"]],
                [["6", "", "", "9", "5000"]],
                [["6", "6", "", "2", "2", "2"]],
                [["6", "25", "1"]],
            ],
            [
                (0, "Target address: 10.96.66.4", []),
                (0, "Source address: 10.96.27.69", []),
                (0, "RTT type: jitter", []),
                (0, "Threshold: 5000 ms", []),
                (0, "State: active", []),
                (0, "Connection lost occured: no", []),
                (0, "Timeout occured: no", []),
                (0, "Completion time over treshold occured: no", []),
                (0, "Latest RTT completion time: 25 ms", [("rtt", 0.025, 0.25, 0.5)]),
                (0, "Latest RTT state: ok", []),
            ],
        ),
    ],
)
def test_check_cisco_ip_sla(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for cisco_ip_sla check."""
    parsed = parse_cisco_ip_sla(string_table)
    result = list(check_cisco_ip_sla(item, params, parsed))
    assert result == expected_results
