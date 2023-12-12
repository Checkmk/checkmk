#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import render


def inventory_innovaphone_mem(info):
    yield None, {}


def check_innovaphone_mem(_no_item, params, info):
    yield check_levels(
        int(info[0][1]),
        "usage",
        params["levels"],
        human_readable_func=render.percent,
        infoname="Current",
    )


check_info["innovaphone_mem"] = LegacyCheckDefinition(
    service_name="Memory",
    discovery_function=inventory_innovaphone_mem,
    check_function=check_innovaphone_mem,
    check_ruleset_name="innovaphone_mem",
    check_default_parameters={
        "levels": (60.0, 70.0),
    },
)
