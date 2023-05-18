#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import discover, get_parsed_item_data, LegacyCheckDefinition
from cmk.base.check_legacy_includes.aws import check_aws_limits, parse_aws_limits_generic
from cmk.base.config import check_info


@get_parsed_item_data
def check_aws_cloudwatch_alarms_limits(item, params, region_data):
    return check_aws_limits("cloudwatch_alarms", params, region_data)


check_info["aws_cloudwatch_alarms_limits"] = LegacyCheckDefinition(
    parse_function=parse_aws_limits_generic,
    discovery_function=discover(),
    check_function=check_aws_cloudwatch_alarms_limits,
    service_name="AWS/CloudWatch Alarms Limits %s",
    check_ruleset_name="aws_cloudwatch_alarms_limits",
    check_default_parameters={
        "cloudwatch_alarms": (None, 80.0, 90.0),
    },
)
