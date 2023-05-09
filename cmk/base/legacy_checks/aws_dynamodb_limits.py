#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import discover, get_parsed_item_data
from cmk.base.check_legacy_includes.aws import check_aws_limits, parse_aws_limits_generic
from cmk.base.config import check_info, factory_settings

factory_settings["aws_dynamodb_limits_default_levels"] = {
    "number_of_tables": (None, 80.0, 90.0),
    "read_capacity": (None, 80.0, 90.0),
    "write_capacity": (None, 80.0, 90.0),
}


@get_parsed_item_data
def check_aws_dynamodb_limits(item, params, region_data):
    return check_aws_limits("dynamodb", params, region_data)


check_info["aws_dynamodb_limits"] = {
    "parse_function": parse_aws_limits_generic,
    "discovery_function": discover(),
    "check_function": check_aws_dynamodb_limits,
    "service_name": "AWS/DynamoDB Limits %s",
    "check_ruleset_name": "aws_dynamodb_limits",
    "default_levels_variable": "aws_dynamodb_limits_default_levels",
}
