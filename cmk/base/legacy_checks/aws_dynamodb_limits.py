#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.aws import check_aws_limits, parse_aws_limits_generic
from cmk.base.config import check_info


def check_aws_dynamodb_limits(item, params, parsed):
    if not (region_data := parsed.get(item)):
        return
    yield from check_aws_limits("dynamodb", params, region_data)


def discover_aws_dynamodb_limits(section):
    yield from ((item, {}) for item in section)


check_info["aws_dynamodb_limits"] = LegacyCheckDefinition(
    parse_function=parse_aws_limits_generic,
    discovery_function=discover_aws_dynamodb_limits,
    check_function=check_aws_dynamodb_limits,
    service_name="AWS/DynamoDB Limits %s",
    check_ruleset_name="aws_dynamodb_limits",
    check_default_parameters={
        "number_of_tables": (None, 80.0, 90.0),
        "read_capacity": (None, 80.0, 90.0),
        "write_capacity": (None, 80.0, 90.0),
    },
)
