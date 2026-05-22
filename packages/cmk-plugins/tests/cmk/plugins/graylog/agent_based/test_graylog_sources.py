#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.plugins.graylog import lib as graylog
from cmk.plugins.graylog.agent_based.graylog_sources import (
    check_graylog_sources,
    parse_graylog_sources,
)


@pytest.mark.parametrize(
    "section, item, expected_check_result",
    [
        pytest.param(
            [['{"sources": {"172.18.0.1": {"messages": 457, "has_since_argument": false}}}']],
            "not_found",
            [],
            id="If the item is not found, there are no results.",
        ),
        pytest.param(
            [['{"sources": {"172.18.0.1": {"messages": 457, "has_since_argument": false}}}']],
            "172.18.0.1",
            [
                Result(state=State.OK, summary="Total number of messages: 457"),
                Metric("messages", 457),
                Result(
                    state=State.OK,
                    summary="Average number of messages (30 minutes 0 seconds): 0.00",
                ),
                Metric("msgs_avg", 0.0),
                Result(
                    state=State.OK,
                    summary="Total number of messages since last check (within 30 minutes 0 seconds): 0",
                ),
                Metric("graylog_diff", 0.0),
            ],
            id="Timeframe for 'source_since' not configured.",
        ),
        pytest.param(
            [
                [
                    '{"sources": {"172.18.0.1": {"messages": 457, "has_since_argument": true, "messages_since": 5, "source_since": 1800}}}'
                ]
            ],
            "172.18.0.1",
            [
                Result(state=State.OK, summary="Total number of messages: 457"),
                Metric("messages", 457),
                Result(
                    state=State.OK,
                    summary="Average number of messages (30 minutes 0 seconds): 0.00",
                ),
                Metric("msgs_avg", 0.0),
                Result(
                    state=State.OK,
                    summary="Total number of messages in the last 30 minutes 0 seconds: 5",
                ),
                Metric("graylog_diff", 5.0),
            ],
            id="Timeframe for 'source_since' configured. Now the check gives information about the total number of messages received in the timeframe.",
        ),
    ],
)
def test_check_graylog_sources(
    monkeypatch: pytest.MonkeyPatch,
    section: StringTable,
    item: str,
    expected_check_result: Sequence[Result | Metric],
) -> None:
    monkeypatch.setattr(
        graylog,
        "get_value_store",
        lambda: {"graylog_msgs_avg.rate": (1670328674.09963, 457)},
    )

    assert (
        list(
            check_graylog_sources(
                item=item,
                params={},
                section=parse_graylog_sources(section),
            )
        )
        == expected_check_result
    )
