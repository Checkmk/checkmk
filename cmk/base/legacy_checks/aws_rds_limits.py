#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import render
from cmk.base.check_legacy_includes.aws import AWSLimitsByRegion, check_aws_limits, parse_aws

check_info = {}


def parse_aws_rds_limits(string_table):
    limits_by_region: AWSLimitsByRegion = {}
    for line in parse_aws(string_table):
        resource_key, resource_title, limit, amount, region = line

        if resource_key == "allocated_storage":
            # Allocated Storage has unit TiB
            factor = 1024**4 / 1000.0
            limit = limit * factor
            amount = amount * factor
            human_readable_f: Callable[[Any], str] | type[int] = render.bytes
        else:
            human_readable_f = int
        limits_by_region.setdefault(region, []).append(
            [resource_key, resource_title, limit, amount, human_readable_f]
        )
    return limits_by_region


def check_aws_rds_limits(item, params, parsed):
    if not (region_data := parsed.get(item)):
        return
    yield from check_aws_limits("rds", params, region_data)


def discover_aws_rds_limits(section):
    yield from ((item, {}) for item in section)


check_info["aws_rds_limits"] = LegacyCheckDefinition(
    name="aws_rds_limits",
    parse_function=parse_aws_rds_limits,
    service_name="AWS/RDS Limits %s",
    discovery_function=discover_aws_rds_limits,
    check_function=check_aws_rds_limits,
    check_ruleset_name="aws_rds_limits",
    check_default_parameters={
        "db_instances": (None, 80.0, 90.0),
        "reserved_db_instances": (None, 80.0, 90.0),
        "allocated_storage": (None, 80.0, 90.0),
        "db_security_groups": (None, 80.0, 90.0),
        "auths_per_db_security_groups": (None, 80.0, 90.0),
        "db_parameter_groups": (None, 80.0, 90.0),
        "manual_snapshots": (None, 80.0, 90.0),
        "event_subscriptions": (None, 80.0, 90.0),
        "db_subnet_groups": (None, 80.0, 90.0),
        "option_groups": (None, 80.0, 90.0),
        "subnet_per_db_subnet_groups": (None, 80.0, 90.0),
        "read_replica_per_master": (None, 80.0, 90.0),
        "db_clusters": (None, 80.0, 90.0),
        "db_cluster_parameter_groups": (None, 80.0, 90.0),
        "db_cluster_roles": (None, 80.0, 90.0),
    },
)
