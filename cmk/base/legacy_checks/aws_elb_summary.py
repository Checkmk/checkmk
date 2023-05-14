#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import discover_single, LegacyCheckDefinition
from cmk.base.check_legacy_includes.aws import check_aws_elb_summary_generic, parse_aws
from cmk.base.config import check_info

check_info["aws_elb_summary"] = LegacyCheckDefinition(
    parse_function=parse_aws,
    discovery_function=discover_single,
    check_function=check_aws_elb_summary_generic,
    service_name="AWS/ELB Summary",
)
