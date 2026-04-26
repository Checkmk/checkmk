#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.aws.agent_based.aws_rds_limits import (
    check_aws_rds_limits,
    discover_aws_rds_limits,
    parse_aws_rds_limits,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([['[["db_instances",', '"TITLE",', "10,", "1,", '"REGION"]]']], [Service(item="REGION")]),
    ],
)
def test_discover_aws_rds_limits(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    """Test discovery function for aws_rds_limits check."""
    parsed = parse_aws_rds_limits(string_table)
    result = list(discover_aws_rds_limits(parsed))
    assert result == expected_discoveries


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "REGION",
            {
                "manual_snapshots": (None, 80.0, 90.0),
                "db_clusters": (None, 80.0, 90.0),
                "db_parameter_groups": (None, 80.0, 90.0),
                "option_groups": (None, 80.0, 90.0),
                "db_cluster_roles": (None, 80.0, 90.0),
                "db_security_groups": (None, 80.0, 90.0),
                "reserved_db_instances": (None, 80.0, 90.0),
                "read_replica_per_master": (None, 80.0, 90.0),
                "event_subscriptions": (None, 80.0, 90.0),
                "subnet_per_db_subnet_groups": (None, 80.0, 90.0),
                "db_cluster_parameter_groups": (None, 80.0, 90.0),
                "allocated_storage": (None, 80.0, 90.0),
                "db_subnet_groups": (None, 80.0, 90.0),
                "db_instances": (None, 80.0, 90.0),
                "auths_per_db_security_groups": (None, 80.0, 90.0),
            },
            [['[["db_instances",', '"TITLE",', "10,", "1,", '"REGION"]]']],
            [
                Metric("aws_rds_db_instances", 1),
                Result(state=State.OK, notice="TITLE: 1 (of max. 10), 10.00%"),
            ],
        ),
        (
            "REGION",
            {
                "db_instances": (None, 80.0, 90.0),
                "db_clusters": (None, 80.0, 90.0),
            },
            [
                [
                    '[["db_instances", "DB instances", 10, 1, "REGION"],'
                    ' ["db_clusters", "DB clusters", 10, 8.5, "REGION"],'
                    ' ["bogus_resource", "Bogus", 10, 1, "REGION"]]'
                ]
            ],
            [
                Metric("aws_rds_db_instances", 1.0),
                Result(state=State.OK, notice="DB instances: 1 (of max. 10), 10.00%"),
                Metric("aws_rds_db_clusters", 8.5),
                Result(
                    state=State.WARN,
                    notice=("DB clusters: 8 (of max. 10), 85.00% (warn/crit at 80.00%/90.00%)"),
                ),
                Result(state=State.UNKNOWN, summary="Unknown resource 'bogus_resource'"),
            ],
        ),
    ],
)
def test_check_aws_rds_limits(
    item: str,
    params: Mapping[str, tuple[float | None, float, float]],
    string_table: StringTable,
    expected_results: Sequence[Result | Metric],
) -> None:
    """Test check function for aws_rds_limits check."""
    parsed = parse_aws_rds_limits(string_table)
    result = list(check_aws_rds_limits(item, params, parsed))
    assert result == expected_results
