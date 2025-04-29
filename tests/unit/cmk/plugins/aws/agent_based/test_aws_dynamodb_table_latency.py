#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, Service, State
from cmk.plugins.aws.agent_based.aws_dynamodb_table_latency import (
    check_aws_dynamodb_latency,
    inventory_aws_dynamodb_latency,
)

test_section = {
    "Query_Average_SuccessfulRequestLatency": 200.0,
    "Query_Maximum_SuccessfulRequestLatency": 500.0,
    "GetItem_Average_SuccessfulRequestLatency": 150.0,
    "GetItem_Maximum_SuccessfulRequestLatency": 400.0,
    "PutItem_Average_SuccessfulRequestLatency": 300.0,
    "PutItem_Maximum_SuccessfulRequestLatency": 600.0,
}

test_params: Mapping[str, tuple[float, float]] = {
    "levels_seconds_query_average": (800, 1000),
    "levels_seconds_query_maximum": (800, 1000),
    "levels_seconds_getitem_maximum": (800, 1000),
    "levels_seconds_getitem_average": (800, 1000),
    "levels_seconds_putitem_maximum": (800, 1000),
    "levels_seconds_putitem_average": (800, 1000),
}


def test_inventory_aws_dynamodb_latency():
    inventory = list(inventory_aws_dynamodb_latency(test_section))
    assert len(inventory) == 1  # Always only one Service
    assert isinstance(inventory[0], Service)


@pytest.mark.parametrize(
    "metric_value, metric_id, expected_summary, expected_metric_name, expected_state",
    [
        pytest.param(
            200.0,
            "Query_Average_SuccessfulRequestLatency",
            "Average latency Query: 200 milliseconds",
            "aws_dynamodb_query_average_latency",
            State.OK,
        ),
        pytest.param(
            500.0,
            "Query_Maximum_SuccessfulRequestLatency",
            "Maximum latency Query: 500 milliseconds",
            "aws_dynamodb_query_maximum_latency",
            State.OK,
        ),
        pytest.param(
            150.0,
            "GetItem_Average_SuccessfulRequestLatency",
            "Average latency GetItem: 150 milliseconds",
            "aws_dynamodb_getitem_average_latency",
            State.OK,
        ),
        pytest.param(
            400.0,
            "GetItem_Maximum_SuccessfulRequestLatency",
            "Maximum latency GetItem: 400 milliseconds",
            "aws_dynamodb_getitem_maximum_latency",
            State.OK,
        ),
        pytest.param(
            1001.0,
            "PutItem_Average_SuccessfulRequestLatency",
            "Average latency PutItem: 1 second (warn/crit at 800 milliseconds/1 second)",
            "aws_dynamodb_putitem_average_latency",
            State.CRIT,
        ),
        pytest.param(
            801.0,
            "PutItem_Maximum_SuccessfulRequestLatency",
            "Maximum latency PutItem: 801 milliseconds (warn/crit at 800 milliseconds/1 second)",
            "aws_dynamodb_putitem_maximum_latency",
            State.WARN,
        ),
    ],
)
def test_check_aws_dynamodb_latency(
    metric_value: float,
    metric_id: str,
    expected_summary: str,
    expected_metric_name: str,
    expected_state: State,
) -> None:
    results = list(check_aws_dynamodb_latency(test_params, {metric_id: metric_value}))
    assert len(results) == 2  # one result and one metric per operation

    assert isinstance(results[0], Result)
    assert results[0].state == expected_state
    assert results[0].summary == expected_summary

    assert isinstance(results[1], Metric)
    assert results[1].name == expected_metric_name
    assert results[1].value == metric_value * 1e-3


def test_check_aws_dynamodb_latency_no_data():
    with pytest.raises(IgnoreResultsError):
        list(check_aws_dynamodb_latency(test_params, {}))
