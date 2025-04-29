#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, Service, State
from cmk.plugins.aws.agent_based.aws_dynamodb_table_read_capacity import (
    check_aws_dynamodb_read_capacity,
    discover_aws_dynamodb_table_read_capacity,
)

test_section = {
    "Sum_ConsumedReadCapacityUnits": 50.0,
    "provisioned_ReadCapacityUnits": 100.0,
    "Minimum_ConsumedReadCapacityUnits": 19.0,
    "Maximum_ConsumedReadCapacityUnits": 80.123,
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
}


def test_discover_aws_dynamodb_table_write_capacity():
    inventory = list(discover_aws_dynamodb_table_read_capacity(test_section))
    assert len(inventory) == 1  # Always only one Service
    assert isinstance(inventory[0], Service)


def test_check_aws_dynamodb_write_capacity():
    results = list(check_aws_dynamodb_read_capacity(test_params, test_section))
    assert len(results) == len(test_section) * 2  # one result and one metric per operation
    assert (
        len(
            [
                res
                for res in results
                if isinstance(res, Metric)
                and res.name.startswith("aws_dynamodb_")
                and (res.name.endswith("_rcu") or res.name.endswith("_perc"))
            ]
        )
        == 4
    )
    assert isinstance(results[0], Result)
    assert results[0].state == State.OK
    assert "Avg. consumption" in results[0].summary
    assert " RCU" in results[0].summary

    assert isinstance(results[2], Result)
    assert results[2].state == State.OK
    assert results[2].summary == "Usage: 50.00%"

    assert isinstance(results[4], Result)
    assert results[4].state == State.WARN
    assert "Min. single-request consumption" in results[4].summary
    assert " RCU" in results[4].summary

    assert isinstance(results[6], Result)
    assert results[6].state == State.CRIT
    assert "Max. single-request consumption" in results[6].summary
    assert " RCU" in results[6].summary


def test_check_aws_dynamodb_latency_no_data():
    with pytest.raises(IgnoreResultsError):
        list(check_aws_dynamodb_read_capacity(test_params, {}))
