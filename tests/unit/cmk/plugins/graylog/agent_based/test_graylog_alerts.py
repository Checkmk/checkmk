#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.graylog.agent_based.alerts import (
    check_graylog_alerts,
    parse_graylog_alerts,
)


@pytest.mark.parametrize(
    "section, expected_check_result",
    [
        pytest.param(
            [['{"alerts": {"num_of_events": 0, "num_of_alerts": 0}}']],
            [
                Result(state=State.OK, summary="Total number of alerts: 0"),
                Metric("graylog_alerts", 0.0),
                Result(state=State.OK, summary="Total number of events: 0"),
                Metric("graylog_events", 0.0),
            ],
            id="No alerts and events.",
        ),
        pytest.param(
            [['{"alerts": {"num_of_events": 53, "num_of_alerts": 0}}']],
            [
                Result(state=State.OK, summary="Total number of alerts: 0"),
                Metric("graylog_alerts", 0.0),
                Result(state=State.OK, summary="Total number of events: 53"),
                Metric("graylog_events", 53.0),
            ],
            id="Events exists and no alerts.",
        ),
        pytest.param(
            [['{"alerts": {"num_of_events": 0, "num_of_alerts": 5}}']],
            [
                Result(state=State.OK, summary="Total number of alerts: 5"),
                Metric("graylog_alerts", 5.0),
                Result(state=State.OK, summary="Total number of events: 0"),
                Metric("graylog_events", 0.0),
            ],
            id="Alerts exists and no events.",
        ),
        pytest.param(
            [['{"alerts": {"num_of_events": 63, "num_of_alerts": 7}}']],
            [
                Result(state=State.OK, summary="Total number of alerts: 7"),
                Metric("graylog_alerts", 7.0),
                Result(state=State.OK, summary="Total number of events: 63"),
                Metric("graylog_events", 63.0),
            ],
            id="Events and alerts exists.",
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
    section = [['{"num_of_events": 0, "num_of_alerts": 0}']]
    parsed_section = parse_graylog_alerts(section)
    assert parsed_section is None
