#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.aws.agent_based.aws_dynamodb_summary import (
    check_aws_dynamodb_summary,
    discover_aws_dynamodb_summary,
)
from cmk.plugins.aws.constants import AWSRegions

test_section = [
    {
        "TableName": "sgr-global-table",
        "TableStatus": "ACTIVE",
        "TableSizeBytes": 123,
        "ItemCount": 2,
        "Region": "eu-central-1",
    },
    {
        "TableName": "sgr-on-demand",
        "TableStatus": "ACTIVE",
        "TableSizeBytes": 1025,
        "ItemCount": 1,
        "Region": "eu-central-1",
    },
    {
        "TableName": "sgr-table",
        "TableStatus": "ACTIVE",
        "TableSizeBytes": 481,
        "ItemCount": 6,
        "Region": "eu-central-1",
    },
    {
        "TableName": "sgr-global-table",
        "TableStatus": "ACTIVE",
        "TableSizeBytes": 123,
        "ItemCount": 2,
        "Region": "us-east-1",
    },
    {
        "TableName": "sgr-us-only-table",
        "TableStatus": "ACTIVE",
        "TableSizeBytes": 456,
        "ItemCount": 4,
        "Region": "us-east-1",
    },
]


def test_discover_aws_dynamodb_summary():
    discovered_services = list(discover_aws_dynamodb_summary(test_section))
    assert len(discovered_services) == 1
    assert isinstance(discovered_services[0], Service)


def test_check_aws_dynamodb_summary():
    check_results = list(check_aws_dynamodb_summary(test_section))
    aws_regions = dict(AWSRegions)

    table_count_result = check_results[0]
    assert isinstance(table_count_result, Result)
    assert table_count_result.state == State.OK
    assert table_count_result.summary.endswith(f" {len(test_section)}")

    count_overall_checks = 2
    table_regions = {entry["Region"] for entry in test_section}
    assert len(check_results) == len(table_regions) + count_overall_checks

    summaries = {result.summary for result in check_results if isinstance(result, Result)}
    assert f"{aws_regions['eu-central-1']}: 3" in summaries
    assert f"{aws_regions['us-east-1']}: 2" in summaries

    # Verify details output
    last_result = check_results[-1]
    assert isinstance(last_result, Result)
    assert "sgr-global-table -- Items: 2, Size: 123 B, Status: ACTIVE" in last_result.details
    assert "sgr-on-demand -- Items: 1, Size: 1.00 KiB, Status: ACTIVE" in last_result.details
    assert "sgr-table -- Items: 6, Size: 481 B, Status: ACTIVE" in last_result.details
    assert "sgr-us-only-table -- Items: 4, Size: 456 B, Status: ACTIVE" in last_result.details
