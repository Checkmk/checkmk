#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.plugins.mongodb.agent_based import connections


@pytest.mark.parametrize(
    "info",
    [
        [("current", "a"), ("available", "10"), ("totalCreated", "257")],
        [("current", "1"), ("available", "a"), ("totalCreated", "257")],
        [("current", "1"), ("available", "10"), ("totalCreated", "a")],
        [("current", ""), ("available", "10"), ("totalCreated", "10000")],
        [("current", "1"), ("available", ""), ("totalCreated", "10000")],
        [("current", "1"), ("available", "10"), ("totalCreated", "")],
    ],
)
def test_check_function_invalid_input_item_not_found(info: StringTable) -> None:
    """
    Checks that invalid input results in "Item not found". Not sure if this is good.
    """

    assert not list(
        connections.check_mongodb_connections(
            "Connections",
            {"levels_perc": (80.0, 90.0)},
            connections.parse_mongodb_connections(info),
        )
    )


@pytest.mark.parametrize(
    "info,expected",
    [
        (
            [("current", "1"), ("available", "1"), ("totalCreated", "1")],
            [
                Result(state=State.OK, summary="Used connections: 1"),
                Metric("connections", 1.0),
                Result(state=State.OK, summary="Used percentage: 50.00%"),
            ],
        ),
        (
            [("current", "10"), ("available", "200"), ("totalCreated", "25007")],
            [
                Result(state=State.OK, summary="Used connections: 10"),
                Metric("connections", 10.0),
                Result(state=State.OK, summary="Used percentage: 4.76%"),
            ],
        ),
    ],
)
def test_check_function(
    monkeypatch: pytest.MonkeyPatch, info: StringTable, expected: Sequence[Result | Metric]
) -> None:
    """
    Checks funny connections values
    """
    monkeypatch.setattr(connections, "get_value_store", lambda: {"total_created": (0.0, 0)})

    result = list(
        connections.check_mongodb_connections(
            "Connections",
            {"levels_perc": (80.0, 90.0)},
            connections.parse_mongodb_connections(info),
        )
    )[:-2]  # we are not testing the get_rate function here assuming it works
    assert result == expected
