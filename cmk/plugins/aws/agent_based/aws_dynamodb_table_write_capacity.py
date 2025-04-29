#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
)
from cmk.plugins.aws.agent_based.aws_dynamodb_table_capacity import (
    aws_dynamodb_table_check_capacity,
)
from cmk.plugins.aws.lib import discover_aws_generic_single


def check_aws_dynamodb_write_capacity(
    params: Mapping[str, Mapping], section: Mapping[str, float]
) -> CheckResult:
    yield from aws_dynamodb_table_check_capacity(
        params.get("levels_write", {}), section, "WriteCapacityUnits"
    )


def discover_aws_dynamodb_table_write_capacity(section: Mapping[str, float]) -> DiscoveryResult:
    yield from discover_aws_generic_single(section, ["Sum_ConsumedWriteCapacityUnits"])


check_plugin_aws_dynamodb_table_write_capacity = CheckPlugin(
    name="aws_dynamodb_table_write_capacity",
    service_name="AWS/DynamoDB Write Capacity",
    sections=["aws_dynamodb_table"],
    discovery_function=discover_aws_dynamodb_table_write_capacity,
    check_function=check_aws_dynamodb_write_capacity,
    check_ruleset_name="aws_dynamodb_capacity",
    check_default_parameters={
        "levels_read": {
            "levels_average": {
                "levels_upper": (80.0, 90.0),
            },
        },
        "levels_write": {
            "levels_average": {
                "levels_upper": (80.0, 90.0),
            },
        },
    },
)
