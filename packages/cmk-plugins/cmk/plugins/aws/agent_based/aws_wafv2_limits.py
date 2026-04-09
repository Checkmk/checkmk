#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
)
from cmk.plugins.aws.lib import check_aws_limits_legacy, parse_aws_limits_generic


def check_aws_wafv2_limits(
    item: str,
    params: Mapping[str, Any],
    section: Mapping[str, list[list]],
) -> CheckResult:
    if not (region_data := section.get(item)):
        return
    yield from check_aws_limits_legacy("wafv2", params, region_data)


def discover_aws_wafv2_limits(section: Mapping[str, list[list]]) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


agent_section_aws_wafv2_limits = AgentSection(
    name="aws_wafv2_limits",
    parse_function=parse_aws_limits_generic,
)


check_plugin_aws_wafv2_limits = CheckPlugin(
    name="aws_wafv2_limits",
    service_name="AWS/WAFV2 Limits %s",
    discovery_function=discover_aws_wafv2_limits,
    check_function=check_aws_wafv2_limits,
    check_ruleset_name="aws_wafv2_limits",
    check_default_parameters={
        "web_acls": (None, 80.0, 90.0),
        "rule_groups": (None, 80.0, 90.0),
        "ip_sets": (None, 80.0, 90.0),
        "regex_pattern_sets": (None, 80.0, 90.0),
        "web_acl_capacity_units": (None, 80.0, 90.0),
    },
)
