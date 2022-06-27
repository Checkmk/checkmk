#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Callable, Mapping

from .agent_based_api.v1 import register, render, Service
from .agent_based_api.v1.type_defs import DiscoveryResult, StringTable
from .utils.aws import AWSLimitsByRegion, check_aws_limits, parse_aws

AWS_EBS_LIMITS_DEFAULT_PARAMS = {
    "block_store_snapshots": (None, 80.0, 90.0),
    "block_store_space_standard": (None, 80.0, 90.0),
    "block_store_space_io1": (None, 80.0, 90.0),
    "block_store_iops_io1": (None, 80.0, 90.0),
    "block_store_space_io2": (None, 80.0, 90.0),
    "block_store_iops_io2": (None, 80.0, 90.0),
    "block_store_space_gp2": (None, 80.0, 90.0),
    "block_store_space_gp3": (None, 80.0, 90.0),
    "block_store_space_sc1": (None, 80.0, 90.0),
    "block_store_space_st1": (None, 80.0, 90.0),
}


def _render_per_second_unit(value: object) -> str:
    return f"{value}/s"


def parse_aws_ebs_limits(string_table: StringTable) -> AWSLimitsByRegion:
    limits_by_region: AWSLimitsByRegion = {}
    for line in parse_aws(string_table):
        resource_key, resource_title, limit, amount, region = line

        if resource_key in [
            "block_store_space_standard",
            "block_store_space_io1",
            "block_store_space_io2",
            "block_store_space_gp2",
            "block_store_space_gp3",
            "block_store_space_sc1",
            "block_store_space_st1",
        ]:
            # Limit has unit TiB, amount is measured in GiB
            limit *= 1024**4
            amount *= 1024**3
            human_readable_func: Callable = render.bytes
        elif resource_key in {"block_store_iops_io1", "block_store_iops_io2"}:
            human_readable_func = _render_per_second_unit
        else:
            human_readable_func = int
        limits_by_region.setdefault(region, []).append(
            [resource_key, resource_title, limit, amount, human_readable_func]
        )
    return limits_by_region


register.agent_section(
    name="aws_ebs_limits",
    parse_function=parse_aws_ebs_limits,
)


def discover_aws_ebs_limits(section: AWSLimitsByRegion) -> DiscoveryResult:
    yield from (Service(item=region) for region in section)


def check_aws_ebs_limits(item: str, params: Mapping[str, Any], section: AWSLimitsByRegion):
    if (region_limits := section.get(item)) is not None:
        yield from check_aws_limits("ebs", params, region_limits)


register.check_plugin(
    name="aws_ebs_limits",
    service_name="AWS/EBS Limits %s",
    discovery_function=discover_aws_ebs_limits,
    check_ruleset_name="aws_ebs_limits",
    check_default_parameters=AWS_EBS_LIMITS_DEFAULT_PARAMS,
    check_function=check_aws_ebs_limits,
)
