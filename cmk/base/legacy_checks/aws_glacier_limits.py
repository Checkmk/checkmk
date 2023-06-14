#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import discover, get_parsed_item_data, LegacyCheckDefinition
from cmk.base.check_legacy_includes.aws import check_aws_limits, parse_aws_limits_generic
from cmk.base.config import check_info

# .
#   .--Glacier limits------------------------------------------------------.
#   |       ____ _            _             _ _           _ _              |
#   |      / ___| | __ _  ___(_) ___ _ __  | (_)_ __ ___ (_) |_ ___        |
#   |     | |  _| |/ _` |/ __| |/ _ \ '__| | | | '_ ` _ \| | __/ __|       |
#   |     | |_| | | (_| | (__| |  __/ |    | | | | | | | | | |_\__ \       |
#   |      \____|_|\__,_|\___|_|\___|_|    |_|_|_| |_| |_|_|\__|___/       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@get_parsed_item_data
def check_aws_glacier_limits(item, params, region_data):
    return check_aws_limits("glacier", params, region_data)


check_info["aws_glacier_limits"] = LegacyCheckDefinition(
    parse_function=parse_aws_limits_generic,
    discovery_function=discover(),
    check_function=check_aws_glacier_limits,
    service_name="AWS/Glacier Limits %s",
    check_ruleset_name="aws_glacier_limits",
    check_default_parameters={
        "number_of_vaults": (None, 80.0, 90.0),
    },
)
