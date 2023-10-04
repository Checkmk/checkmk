#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info


def inventory_symantec_av_progstate(info):
    return [(None, None)]


def check_symantec_av_progstate(_no_item, _no_params, info):
    if info[0][0].lower() != "enabled":
        return 2, "Program Status is " + info[0][0]
    return 0, "Program enabled"


check_info["symantec_av_progstate"] = LegacyCheckDefinition(
    service_name="AV Program Status",
    discovery_function=inventory_symantec_av_progstate,
    check_function=check_symantec_av_progstate,
)
