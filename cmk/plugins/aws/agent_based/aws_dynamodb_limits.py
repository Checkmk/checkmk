#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Literal

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
)
from cmk.plugins.aws.lib import (
    AWSLimits,
    check_aws_limits,
    parse_aws_limits_generic,
)


def check_aws_dynamodb_limits(
    item: str,
    params: Mapping[
        str, tuple[Literal["no_levels"], None] | tuple[Literal["set_levels"], AWSLimits]
    ],
    section: Mapping[str, list[list]],
) -> CheckResult:
    if not (region_data := section.get(item)):
        return
    yield from check_aws_limits("dynamodb", params, region_data)


def discover_aws_dynamodb_limits(section: Mapping[str, list[list]]) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


agent_section_aws_dynamodb_limits = AgentSection(
    name="aws_dynamodb_limits",
    parse_function=parse_aws_limits_generic,
)

check_plugin_aws_dynamodb_limits = CheckPlugin(
    name="aws_dynamodb_limits",
    service_name="AWS/DynamoDB Limits %s",
    discovery_function=discover_aws_dynamodb_limits,
    check_function=check_aws_dynamodb_limits,
    sections=["aws_dynamodb_limits"],
    check_ruleset_name="aws_dynamodb_limits",
    check_default_parameters={
        "number_of_tables": (
            "set_levels",
            {
                "absolute": ("aws_default_limit", None),
                "percentage": {"warn": 80.0, "crit": 90.0},
            },
        ),
        "read_capacity": (
            "set_levels",
            {
                "absolute": ("aws_default_limit", None),
                "percentage": {"warn": 80.0, "crit": 90.0},
            },
        ),
        "write_capacity": (
            "set_levels",
            {
                "absolute": ("aws_default_limit", None),
                "percentage": {"warn": 80.0, "crit": 90.0},
            },
        ),
    },
)
