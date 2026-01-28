#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.agent_based.legacy.v0_unstable import (
    LegacyCheckDefinition,
    LegacyCheckResult,
    LegacyDiscoveryResult,
)
from cmk.base.check_legacy_includes.aws import (
    AWSLimitsByRegion,
    check_aws_limits,
    parse_aws_limits_generic,
)

check_info = {}


def check_aws_elb_limits(
    item: str, params: Mapping[str, tuple[float | None, float, float]], parsed: AWSLimitsByRegion
) -> LegacyCheckResult:
    if not (region_data := parsed.get(item)):
        return
    yield from check_aws_limits("elb", params, region_data)


def discover_aws_elb_limits(section: AWSLimitsByRegion) -> LegacyDiscoveryResult:
    yield from ((item, {}) for item in section)


check_info["aws_elb_limits"] = LegacyCheckDefinition(
    name="aws_elb_limits",
    parse_function=parse_aws_limits_generic,
    service_name="AWS/ELB Limits %s",
    discovery_function=discover_aws_elb_limits,
    check_function=check_aws_elb_limits,
    check_ruleset_name="aws_elb_limits",
    check_default_parameters={
        "load_balancers": (None, 80.0, 90.0),
        "load_balancer_listeners": (None, 80.0, 90.0),
        "load_balancer_registered_instances": (None, 80.0, 90.0),
    },
)
