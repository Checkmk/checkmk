#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.aws.agent_based.aws_dynamodb_limits import (
    _rewrite_params_to_vs_format,
    check_aws_dynamodb_limits,
    discover_aws_dynamodb_limits,
)
from cmk.plugins.aws.rulesets.aws_dynamodb_limits import AWSLimits


def test_rewrite_params_to_vs_format_no_levels() -> None:
    result = _rewrite_params_to_vs_format({"number_of_tables": ("no_levels", None)})
    assert result == {"number_of_tables": (None, None, None)}


def test_rewrite_params_to_vs_format_with_levels() -> None:
    limits: AWSLimits = {
        "absolute": ("aws_limit_value", 1001),
        "percentage": {"warn": 80.1, "crit": 90.1},
    }
    result = _rewrite_params_to_vs_format({"read_capacity": ("set_levels", limits)})
    assert result == {"read_capacity": (1001, 80.1, 90.1)}


def test_check_aws_dynamodb_limits_no_region_data() -> None:
    item = "us-east-1"
    results = list(check_aws_dynamodb_limits(item, params={}, section={}))
    assert results == []


def test_check_aws_dynamodb_limits_with_region_data() -> None:
    item = "us-east-1"
    limit_number_of_tables: AWSLimits = {
        "absolute": ("aws_limit_value", 256),
        "percentage": {"warn": 80.0, "crit": 90.0},
    }
    limit_read_capacity: AWSLimits = {
        "absolute": ("aws_limit_value", 80000),
        "percentage": {"warn": 75.0, "crit": 90.0},
    }
    limit_write_capacity: AWSLimits = {
        "absolute": ("aws_limit_value", 50000),
        "percentage": {"warn": 75.0, "crit": 90.0},
    }
    section = {
        "us-east-1": [
            ["number_of_tables", "Number of tables", 256, 200, lambda x: f"{x} tables"],
            ["read_capacity", "Read Capacity", 80000, 60000, lambda x: f"{x} RCU"],
            ["write_capacity", "Write Capacity", 80000, 49990, lambda x: f"{x} WCU"],
        ],
    }

    results = list(
        check_aws_dynamodb_limits(
            item,
            {
                "number_of_tables": ("set_levels", limit_number_of_tables),
                "read_capacity": ("set_levels", limit_read_capacity),
                "write_capacity": ("set_levels", limit_write_capacity),
            },
            section,
        )
    )

    assert len(results) == len(section[item]) * 2
    assert isinstance(results[0], Metric) and isinstance(results[1], Result)
    assert isinstance(results[2], Metric) and isinstance(results[3], Result)
    assert isinstance(results[4], Metric) and isinstance(results[5], Result)
    assert results[1].state == State.OK
    assert results[3].state == State.WARN
    assert results[5].state == State.CRIT


def test_discover_aws_dynamodb_limits() -> None:
    services = list(discover_aws_dynamodb_limits(section={"us-east-1": [], "us-west-2": []}))
    assert len(services) == 2
    assert services == [Service(item="us-east-1"), Service(item="us-west-2")]
