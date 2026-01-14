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
from cmk.base.legacy_checks.mq_queues import check_mq_queues, discover_mq_queues, parse_mq_queues


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["[[Queue_App1_App2]]"], ["1", "2", "3", "4"]], [("Queue_App1_App2", {})]),
    ],
)
def test_discover_mq_queues(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for mq_queues check."""
    parsed = parse_mq_queues(string_table)
    result = list(discover_mq_queues(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "Queue_App1_App2",
            {
                "consumer_count_levels_upper": None,
                "consumer_count_levels_lower": None,
                "size": (None, None),
            },
            [["[[Queue_App1_App2]]"], ["1", "2", "3", "4"]],
            [
                (0, "Queue size: 1", [("queue", 1, None, None)]),
                (0, "Enqueue count: 3", [("enque", 3, None, None)]),
                (0, "Dequeue count: 4", [("deque", 4, None, None)]),
            ],
        ),
        (
            "M2M_DC_MGMT",
            {
                "consumer_count_levels_upper": (5, 9),
                "consumer_count_levels_lower": (3, 1),
                "size": (6, 10),
            },
            [["[[M2M_DC_MGMT]]"], ["0", "12", "9193", "9193"]],
            [
                (
                    2,
                    "Consuming connections: 12 (warn/crit at 5/9)",
                    [],
                ),
                (0, "Queue size: 0", [("queue", 0, 6, 10)]),
                (0, "Enqueue count: 9193", [("enque", 9193, None, None)]),
                (0, "Dequeue count: 9193", [("deque", 9193, None, None)]),
            ],
        ),
        (
            "M2M_DATA_RESPONSE",
            {
                "consumer_count_levels_upper": (5, 9),
                "consumer_count_levels_lower": (3, 1),
                "size": (6, 10),
            },
            [["[[M2M_DATA_RESPONSE]]"], ["0", "1", "9193", "9193"]],
            [
                (
                    1,
                    "Consuming connections: 1 (warn/crit below 3/1)",
                    [],
                ),
                (0, "Queue size: 0", [("queue", 0, 6, 10)]),
                (0, "Enqueue count: 9193", [("enque", 9193, None, None)]),
                (0, "Dequeue count: 9193", [("deque", 9193, None, None)]),
            ],
        ),
        (
            "IIS_NMS_MGMT",
            {
                "consumer_count_levels_upper": (5, 9),
                "consumer_count_levels_lower": None,
                "size": (6, 10),
            },
            [["[[IIS_NMS_MGMT]]"], ["0", "12", "9193", "9193"]],
            [
                (
                    2,
                    "Consuming connections: 12 (warn/crit at 5/9)",
                    [],
                ),
                (0, "Queue size: 0", [("queue", 0, 6, 10)]),
                (0, "Enqueue count: 9193", [("enque", 9193, None, None)]),
                (0, "Dequeue count: 9193", [("deque", 9193, None, None)]),
            ],
        ),
        (
            "IIS_FW_UPGRADE_DWNLD",
            {
                "consumer_count_levels_upper": None,
                "consumer_count_levels_lower": (13, 5),
                "size": (6, 10),
            },
            [["[[IIS_FW_UPGRADE_DWNLD]]"], ["0", "4", "9193", "9193"]],
            [
                (
                    2,
                    "Consuming connections: 4 (warn/crit below 13/5)",
                    [],
                ),
                (0, "Queue size: 0", [("queue", 0, 6, 10)]),
                (0, "Enqueue count: 9193", [("enque", 9193, None, None)]),
                (0, "Dequeue count: 9193", [("deque", 9193, None, None)]),
            ],
        ),
    ],
)
def test_check_mq_queues(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for mq_queues check."""
    parsed = parse_mq_queues(string_table)
    result = list(check_mq_queues(item, params, parsed))
    assert result == expected_results
