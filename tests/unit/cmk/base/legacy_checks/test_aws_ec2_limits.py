#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_legacy_includes.aws import parse_aws_limits_generic
from cmk.base.legacy_checks.aws_ec2_limits import check_aws_ec2_limits

from cmk.agent_based.v2 import Metric, Result, State


def test_unlisted_instance_type_reports_usage_without_levels() -> None:
    section = parse_aws_limits_generic(
        [
            [
                '[["running_ondemand_instances_unlisted.xlarge",',
                '"Running On-Demand unlisted.xlarge Instances",',
                "20,",
                "40,",
                '"REGION"]]',
            ]
        ]
    )

    results = list(check_aws_ec2_limits("REGION", {}, section))

    assert results == [
        (0, "No levels reached", []),
        Metric("aws_ec2_running_ondemand_instances_unlisted.xlarge", 40.0),
        Result(
            state=State.OK,
            summary="1 unrecognized instance type (limits not checked)",
            details="Instance types unknown to Checkmk, no limits checked: unlisted.xlarge (40)",
        ),
    ]


def test_listed_instance_type_keeps_levels_next_to_unlisted_type() -> None:
    section = parse_aws_limits_generic(
        [
            [
                '[["running_ondemand_instances_a1.xlarge",',
                '"Running On-Demand a1.xlarge Instances",',
                "20,",
                "19,",
                '"REGION"],',
                '["running_ondemand_instances_unlisted.xlarge",',
                '"Running On-Demand unlisted.xlarge Instances",',
                "20,",
                "1,",
                '"REGION"]]',
            ]
        ]
    )

    results = list(check_aws_ec2_limits("REGION", {}, section))

    assert results == [
        (
            2,
            "Levels reached: Running On-Demand a1.xlarge Instances",
            [("aws_ec2_running_ondemand_instances_a1.xlarge", 19)],
        ),
        (
            2,
            "\nRunning On-Demand a1.xlarge Instances: 19 (of max. 20), "
            "Usage: 95.00% (warn/crit at 80.00%/90.00%)",
        ),
        Metric("aws_ec2_running_ondemand_instances_unlisted.xlarge", 1.0),
        Result(
            state=State.OK,
            summary="1 unrecognized instance type (limits not checked)",
            details="Instance types unknown to Checkmk, no limits checked: unlisted.xlarge (1)",
        ),
    ]


def test_summary_counts_the_unlisted_instance_types() -> None:
    section = parse_aws_limits_generic(
        [
            [
                '[["running_ondemand_instances_unlisted.xlarge",',
                '"Running On-Demand unlisted.xlarge Instances",',
                "20,",
                "3,",
                '"REGION"],',
                '["running_ondemand_instances_unlisted.2xlarge",',
                '"Running On-Demand unlisted.2xlarge Instances",',
                "20,",
                "5,",
                '"REGION"]]',
            ]
        ]
    )

    results = list(check_aws_ec2_limits("REGION", {}, section))

    assert results[-1] == Result(
        state=State.OK,
        summary="2 unrecognized instance types (limits not checked)",
        details="Instance types unknown to Checkmk, no limits checked: unlisted.xlarge (3), unlisted.2xlarge (5)",
    )
