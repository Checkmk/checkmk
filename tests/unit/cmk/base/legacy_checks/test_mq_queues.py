#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.mq_queues import check_mq_queues, inventory_mq_queues, parse_mq_queues


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["[[Queue_App1_App2]]"], ["1", "2", "3", "4"]], [("Queue_App1_App2", {})]),
    ],
)
def test_inventory_mq_queues(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for mq_queues check."""
    parsed = parse_mq_queues(string_table)
    result = list(inventory_mq_queues(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "Queue_App1_App2",
            {"consumerCount": (None, None), "size": (None, None)},
            [["[[Queue_App1_App2]]"], ["1", "2", "3", "4"]],
            [
                (0, "Queue size: 1", [("queue", 1, None, None)]),
                (0, "Enqueue count: 3", [("enque", 3, None, None)]),
                (0, "Dequeue count: 4", [("deque", 4, None, None)]),
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
