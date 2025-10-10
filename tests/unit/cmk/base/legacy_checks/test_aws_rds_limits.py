#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.aws_rds_limits import (
    check_aws_rds_limits,
    discover_aws_rds_limits,
    parse_aws_rds_limits,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([['[["db_instances",', '"TITLE",', "10,", "1,", '"REGION"]]']], [("REGION", {})]),
    ],
)
def test_discover_aws_rds_limits(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for aws_rds_limits check."""
    parsed = parse_aws_rds_limits(string_table)
    result = list(discover_aws_rds_limits(parsed))
    assert sorted(result) == sorted(expected_discoveries)


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
                (0, "No levels reached", [("aws_rds_db_instances", 1)]),
                (0, "\nTITLE: 1 (of max. 10)"),
            ],
        ),
    ],
)
def test_check_aws_rds_limits(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for aws_rds_limits check."""
    parsed = parse_aws_rds_limits(string_table)
    result = list(check_aws_rds_limits(item, params, parsed))
    assert result == expected_results
