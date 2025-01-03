#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.cisco_sma.agent_based.mail_queue import (
    _check_mail_queue,
    _discover_queue,
    _parse_mail_queue,
    Params,
)


@pytest.mark.parametrize(
    "string_table",
    [
        ([["10", "2", "30", "40"]]),
    ],
)
def test_discover_queue(string_table: StringTable) -> None:
    queue = _parse_mail_queue(string_table)
    assert queue is not None
    assert list(_discover_queue(queue)) == [Service()]


@pytest.mark.parametrize(
    "params, string_table, expected",
    (
        (
            Params(
                monitoring_status_memory_available=State.OK.value,
                monitoring_status_memory_shortage=State.WARN.value,
                monitoring_status_queue_full=State.CRIT.value,
                monitoring_status_percent_queue_utilization=("fixed", (80.0, 90.0)),
                monitoring_status_work_queue_messages=("fixed", (500, 1000)),
                monitoring_status_oldest_message_age=("no_levels", None),
            ),
            [["10", "2", "300", "400"]],
            [
                Result(state=State.WARN, summary="Memory shortage"),
                Result(state=State.OK, summary="Utilization: 10.00%"),
                Metric("cisco_sma_queue_utilization", 10.0, levels=(80.0, 90.0)),
                Result(state=State.OK, notice="Total messages: 300.00"),
                Metric("cisco_sma_queue_length", 300.0, levels=(500.0, 1000.0)),
                Result(state=State.OK, notice="Oldest message age: 6 minutes 40 seconds"),
                Metric("cisco_sma_queue_oldest_message_age", 400.0),
            ],
        ),
        (
            Params(
                monitoring_status_memory_available=State.OK.value,
                monitoring_status_memory_shortage=State.WARN.value,
                monitoring_status_queue_full=State.CRIT.value,
                monitoring_status_percent_queue_utilization=("fixed", (80.0, 90.0)),
                monitoring_status_work_queue_messages=("fixed", (500, 1000)),
                monitoring_status_oldest_message_age=("fixed", (3000, 3600)),
            ),
            [["85", "2", "700", "3600"]],
            [
                Result(state=State.WARN, summary="Memory shortage"),
                Result(
                    state=State.WARN, summary="Utilization: 85.00% (warn/crit at 80.00%/90.00%)"
                ),
                Metric("cisco_sma_queue_utilization", 85.0, levels=(80.0, 90.0)),
                Result(
                    state=State.WARN, summary="Total messages: 700.00 (warn/crit at 500.00/1000.00)"
                ),
                Metric("cisco_sma_queue_length", 700.0, levels=(500.0, 1000.0)),
                Result(
                    state=State.CRIT,
                    summary="Oldest message age: 1 hour 0 minutes (warn/crit at 50 minutes 0 seconds/1 hour 0 minutes)",
                ),
                Metric("cisco_sma_queue_oldest_message_age", 3600.0, levels=(3000.0, 3600.0)),
            ],
        ),
    ),
)
def test_check_mail_queue(
    params: Params,
    string_table: StringTable,
    expected: CheckResult,
) -> None:
    queue = _parse_mail_queue(string_table)
    assert queue is not None
    assert list(_check_mail_queue(params, queue)) == list(expected)
