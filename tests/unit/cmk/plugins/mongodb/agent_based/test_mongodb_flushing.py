#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

import pytest

from cmk.agent_based.v2 import Result
from cmk.plugins.mongodb.agent_based.mongodb_flushing import (
    check_mongodb_flushing,
    parse_mongodb_flushing,
)

# <<<mongodb_flushing>>>
# average_ms 1.28893335892
# last_ms 0
# flushed 36479


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "info,expected_results",
    [
        (
            [("average_ms", "1.28893335892"), ("last_ms", "0"), ("flushed", "36479")],
            [
                "Average flush time over 60 minutes: 0.0 ms",
                "Last flush time: 0.00 s",
                "Flushes since restart: 36479.00",
                "Average flush time: 1 millisecond",
            ],
        ),
        (
            [("average_ms", "5"), ("last_ms", "121"), ("flushed", "10000")],
            [
                "Average flush time over 60 minutes: 121.0 ms (warn/crit at 1.0 ms/4.0 ms)",
                "Last flush time: 0.12 s (warn/crit at 0.10 s/0.20 s)",
                "Flushes since restart: 10000.00",
                "Average flush time: 5 milliseconds",
            ],
        ),
        (
            [("last_ms", "120"), ("flushed", "10000")],
            ["missing data: average_ms"],
        ),
        (
            [("average_ms", "5"), ("flushed", "10000")],
            ["missing data: last_ms"],
        ),
        (
            [("average_ms", "5"), ("last_ms", "120")],
            ["missing data: flushed"],
        ),
        (
            [("last_ms", "120")],
            ["missing data: average_ms and flushed"],
        ),
        (
            [],
            ["missing data: average_ms and flushed and last_ms"],
        ),
    ],
)
def test_check_function(info, expected_results):
    """
    Test the MongoDB flushing check function with various input combinations.
    """
    check_result = list(
        check_mongodb_flushing(
            {"average_time": (1, 4, 60), "last_time": (0.1, 0.2)},
            parse_mongodb_flushing(info),
        )
    )

    # Extract summaries from Result objects for comparison
    actual_summaries = []
    for result in check_result:
        if isinstance(result, Result):
            actual_summaries.append(result.summary)

    # Check that we got the expected number of results and they contain the expected messages
    assert len(actual_summaries) >= len(expected_results)
    for expected in expected_results:
        assert any(expected in summary for summary in actual_summaries), (
            f"Expected '{expected}' not found in {actual_summaries}"
        )
