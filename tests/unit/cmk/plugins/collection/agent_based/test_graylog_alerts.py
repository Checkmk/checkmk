#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.agent_based.v2 import Result, State
from cmk.plugins.collection.agent_based.graylog_alerts import (
    check_graylog_alerts,
    parse_graylog_alerts,
)


@pytest.mark.parametrize(
    "section, expected_check_result",
    [
        pytest.param(
            [
                [
                    '{"alerts": {"num_of_alerts": 0, "has_since_argument": false, "alerts_since": null, "num_of_alerts_in_range": 0}}'
                ]
            ],
            [Result(state=State.OK, summary="Total number of alerts: 0")],
            id="Timeframe for 'alerts_since' not configured.",
        ),
        pytest.param(
            [
                [
                    '{"alerts": {"num_of_alerts": 5, "has_since_argument": true, "alerts_since": 1800, "num_of_alerts_in_range": 2}}'
                ]
            ],
            [
                Result(state=State.OK, summary="Total number of alerts: 5"),
                Result(
                    state=State.OK,
                    summary="Total number of alerts in the last 30 minutes 0 seconds: 2",
                ),
            ],
            id="Timeframe for 'alerts_since' configured. Now the check gives information about the total number of alerts received in the timeframe.",
        ),
    ],
)
def test_check_graylog_alerts(
    section: StringTable,
    expected_check_result: Sequence[Result],
) -> None:
    parsed_section = parse_graylog_alerts(section)
    assert parsed_section
    assert (
        list(
            check_graylog_alerts(
                params={},
                section=parsed_section,
            )
        )
        == expected_check_result
    )


def test_parse_graylog_alerts_empty_alerts_section() -> None:
    section = [['{"total": 0, "alerts": []}']]
    parsed_section = parse_graylog_alerts(section)
    assert parsed_section is None
