#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.aws import check_aws_limits, parse_aws_limits_generic

check_info = {}


def check_aws_elbv2_limits(item, params, parsed):
    if not (region_data := parsed.get(item)):
        return
    yield from check_aws_limits("elbv2", params, region_data)


def discover_aws_elbv2_limits(section):
    yield from ((item, {}) for item in section)


check_info["aws_elbv2_limits"] = LegacyCheckDefinition(
    name="aws_elbv2_limits",
    parse_function=parse_aws_limits_generic,
    service_name="AWS/ELBv2 Limits %s",
    discovery_function=discover_aws_elbv2_limits,
    check_function=check_aws_elbv2_limits,
    check_ruleset_name="aws_elbv2_limits",
    check_default_parameters={
        "application_load_balancers": (None, 80.0, 90.0),
        "application_load_balancer_rules": (None, 80.0, 90.0),
        "application_load_balancer_listeners": (None, 80.0, 90.0),
        "application_load_balancer_target_groups": (None, 80.0, 90.0),
        "application_load_balancer_certificates": (None, 80.0, 90.0),
        "network_load_balancers": (None, 80.0, 90.0),
        "network_load_balancer_listeners": (None, 80.0, 90.0),
        "network_load_balancer_target_groups": (None, 80.0, 90.0),
        "load_balancer_target_groups": (None, 80.0, 90.0),
    },
)
