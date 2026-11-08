#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping, Sequence
from typing import Any

import cmk.plugins.aws_deprecated.constants as aws_types
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
)
from cmk.plugins.aws_deprecated.lib import (
    AWSLimitsByRegion,
    check_aws_limits_legacy,
    parse_aws_limits_generic,
)

DEFAULT_LEVELS = (None, 80.0, 90.0)

default_running_ondemand_instances = [
    (inst_type, DEFAULT_LEVELS) for inst_type in aws_types.AWS_EC2_INST_TYPES
]

default_running_ondemand_instance_families = [
    (f"{inst_fam}_vcpu", DEFAULT_LEVELS) for inst_fam in aws_types.AWS_EC2_INST_FAMILIES
]

DEFAULT_PARAMS = {
    "vpc_elastic_ip_addresses": DEFAULT_LEVELS,
    "elastic_ip_addresses": DEFAULT_LEVELS,
    "vpc_sec_group_rules": DEFAULT_LEVELS,
    "vpc_sec_groups": DEFAULT_LEVELS,
    "if_vpc_sec_group": DEFAULT_LEVELS,
    "spot_inst_requests": DEFAULT_LEVELS,
    "active_spot_fleet_requests": DEFAULT_LEVELS,
    "spot_fleet_total_target_capacity": DEFAULT_LEVELS,
    "running_ondemand_instances_total": DEFAULT_LEVELS,
    "running_ondemand_instances": default_running_ondemand_instances,
    "running_ondemand_instances_vcpus": default_running_ondemand_instance_families,
    "unknown_instance_types_state": int(State.WARN),
}

_INSTANCE_TYPE_PREFIX = "running_ondemand_instances_"


def _transform_ec2_limits(params: Mapping[str, Any]) -> dict[str, Any]:
    # Check default reset
    def instance_limits(limits: Sequence[tuple[str, Any]]) -> dict[str, Any]:
        return {f"running_ondemand_instances_{inst_type}": levels for inst_type, levels in limits}

    transformed = instance_limits(default_running_ondemand_instances)
    transformed.update(instance_limits(default_running_ondemand_instance_families))

    for k, v in params.items():
        if isinstance(v, tuple):
            transformed[k] = v
        elif isinstance(v, list):
            transformed.update(instance_limits(v))
    return transformed


def check_aws_ec2_limits(
    item: str, params: Mapping[str, Any], section: AWSLimitsByRegion
) -> CheckResult:
    if not (region_data := section.get(item)):
        return
    # params look like:
    # {'vpc_sec_group_rules': (50, 80.0, 90.0),
    #  'running_ondemand_instances': [('a1.4xlarge', (20, 80.0, 90.0))]}
    limits = _transform_ec2_limits(params)
    # AWS releases instance types faster than AWS_EC2_INST_TYPES is updated
    listed_data = [row for row in region_data if not _is_unlisted_instance_type(row[0], limits)]
    unlisted_data = [row for row in region_data if _is_unlisted_instance_type(row[0], limits)]
    yield from check_aws_limits_legacy("ec2", limits, listed_data)
    yield from _check_unlisted_instance_types(
        unlisted_data,
        State(params["unknown_instance_types_state"]),
    )


def _is_unlisted_instance_type(resource_key: str, limits: Mapping[str, Any]) -> bool:
    return resource_key.startswith(_INSTANCE_TYPE_PREFIX) and resource_key not in limits


def _check_unlisted_instance_types(
    region_data: Sequence[Sequence[Any]],
    not_found_state: State,
) -> CheckResult:
    if not region_data:
        return
    usage: dict[str, int] = {}
    for resource_key, _title, _limit, amount, _render in region_data:
        yield Metric(f"aws_ec2_{resource_key}", amount)
        usage[resource_key.removeprefix(_INSTANCE_TYPE_PREFIX)] = amount
    yield Result(
        state=not_found_state,
        summary="%d unrecognized instance type%s (limits not checked)"
        % (len(usage), "" if len(usage) == 1 else "s"),
        details="Instance types unknown to Checkmk, no limits checked: %s"
        % ", ".join(f"{inst_type} ({amount})" for inst_type, amount in usage.items()),
    )


def discover_aws_ec2_limits(section: AWSLimitsByRegion) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


agent_section_aws_ec2_limits = AgentSection(
    name="aws_ec2_limits",
    parse_function=parse_aws_limits_generic,
)


check_plugin_aws_ec2_limits = CheckPlugin(
    name="aws_ec2_limits",
    service_name="AWS/EC2 Limits %s",
    discovery_function=discover_aws_ec2_limits,
    check_function=check_aws_ec2_limits,
    check_ruleset_name="aws_ec2_limits",
    check_default_parameters=DEFAULT_PARAMS,
)
