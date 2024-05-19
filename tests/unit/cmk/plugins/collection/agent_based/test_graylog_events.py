#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, State, StringTable
from cmk.plugins.collection.agent_based.graylog_events import (
    check_graylog_events,
    parse_graylog_events,
)


@pytest.mark.parametrize(
    "section, expected_check_result",
    [
        pytest.param(
            [
                [
                    '{"events": {"num_of_events": 3, "has_since_argument": false, "events_since": null, "num_of_events_in_range": 0}}'
                ]
            ],
            [Result(state=State.OK, summary="Total number of events in the last 24 hours: 3")],
            id="Timeframe for 'events_since' not configured.",
        ),
        pytest.param(
            [
                [
                    '{"events": {"num_of_events": 5, "has_since_argument": true, "events_since": 1800, "num_of_events_in_range": 2}}'
                ]
            ],
            [
                Result(state=State.OK, summary="Total number of events in the last 24 hours: 5"),
                Result(
                    state=State.OK,
                    summary="Total number of events in the last 30 minutes 0 seconds: 2",
                ),
            ],
            id="Timeframe for 'events_since' configured. Now the check gives information about the total number of events received in the timeframe.",
        ),
    ],
)
def test_check_graylog_events(
    section: StringTable,
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_graylog_events(
                params={},
                section=parse_graylog_events(section),
            )
        )
        == expected_check_result
    )
