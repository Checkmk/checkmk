#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.aws.agent_based.aws_dynamodb_table_capacity import (
    aws_dynamodb_capacity_get_metric_name_and_unit,
    aws_dynamodb_table_check_capacity,
)

test_section_write = {
    "Sum_ConsumedWriteCapacityUnits": 50.0,
    "provisioned_WriteCapacityUnits": 100.0,
    "Minimum_ConsumedWriteCapacityUnits": 25.0,
    "Maximum_ConsumedWriteCapacityUnits": 50.0,
}
test_section_read = {
    "Sum_ConsumedReadCapacityUnits": 50.0,
    "provisioned_ReadCapacityUnits": 100.0,
    "Minimum_ConsumedReadCapacityUnits": 25.0,
    "Maximum_ConsumedReadCapacityUnits": 50.0,
}

test_params: Mapping[str, Mapping] = {
    "levels_read": {
        "levels_average": {
            "limit": 100.0,
            "levels_upper": (75.0, 80.0),
            "levels_lower": (10.0, 15.0),
        },
        "levels_minimum": {"levels_upper": (75.0, 80.0), "levels_lower": (20.0, 15.0)},
        "levels_maximum": {"levels_upper": (75.0, 80.0), "levels_lower": (20.0, 15.0)},
    },
    "levels_write": {
        "levels_average": {
            "limit": 100.0,
            "levels_upper": (75.0, 80.0),
            "levels_lower": (10.0, 15.0),
        },
        "levels_minimum": {"levels_upper": (75.0, 80.0), "levels_lower": (20.0, 15.0)},
        "levels_maximum": {"levels_upper": (75.0, 80.0), "levels_lower": (20.0, 15.0)},
    },
}


def test_aws_dynamodb_table_check_capacity_read_capacity():
    capacity_units_to_check = "ReadCapacityUnits"
    results = list(
        aws_dynamodb_table_check_capacity(
            test_params["levels_read"], test_section_read, capacity_units_to_check
        )
    )

    assert len(results) == len(test_section_read) * 2
    metric_list = [r for r in results if isinstance(r, Metric)]
    result_list = [r for r in results if isinstance(r, Result)]
    assert len(metric_list) == 4
    assert len(result_list) == 4

    assert all(r.state == State.OK for r in result_list)


def test_aws_dynamodb_table_check_capacity_write_capacity():
    capacity_units_to_check = "WriteCapacityUnits"
    results = list(
        aws_dynamodb_table_check_capacity(
            test_params["levels_write"], test_section_write, capacity_units_to_check
        )
    )

    assert len(results) == len(test_section_write) * 2
    metric_list = [r for r in results if isinstance(r, Metric)]
    result_list = [r for r in results if isinstance(r, Result)]
    assert len(metric_list) == 4
    assert len(result_list) == 4

    assert all(r.state == State.OK for r in result_list)


def test_aws_dynamodb_capacity_get_metric_name_and_unit():
    metric_name, unit = aws_dynamodb_capacity_get_metric_name_and_unit(
        "Sum_ConsumedReadCapacityUnits"
    )
    assert metric_name == "aws_dynamodb_consumed_rcu"
    assert unit == "RCU"

    metric_name, unit = aws_dynamodb_capacity_get_metric_name_and_unit(
        "Maximum_ConsumedWriteCapacityUnits"
    )
    assert metric_name == "aws_dynamodb_maximum_consumed_wcu"
    assert unit == "WCU"
