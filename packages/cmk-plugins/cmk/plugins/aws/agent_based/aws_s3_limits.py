#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
)
from cmk.plugins.aws.lib import AWSLimitsByRegion, check_aws_limits_legacy, parse_aws_limits_generic


def check_aws_s3_limits(
    item: str, params: Mapping[str, Any], section: AWSLimitsByRegion
) -> CheckResult:
    if not (region_data := section.get(item)):
        return
    yield from check_aws_limits_legacy("s3", params, region_data)


def discover_aws_s3_limits(section: AWSLimitsByRegion) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


agent_section_aws_s3_limits = AgentSection(
    name="aws_s3_limits",
    parse_function=parse_aws_limits_generic,
)


check_plugin_aws_s3_limits = CheckPlugin(
    name="aws_s3_limits",
    service_name="AWS/S3 Limits %s",
    discovery_function=discover_aws_s3_limits,
    check_function=check_aws_s3_limits,
    check_ruleset_name="aws_s3_limits",
    check_default_parameters={
        "buckets": (None, 80.0, 90.0),
    },
)
