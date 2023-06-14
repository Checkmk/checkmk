#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.innovaphone import check_innovaphone
from cmk.base.config import check_info

innovaphone_mem_default_levels = (60.0, 70.0)


def inventory_innovaphone_mem(info):
    return [(None, innovaphone_mem_default_levels)]


def check_innovaphone_mem(_no_item, params, info):
    return check_innovaphone(params, info)


check_info["innovaphone_mem"] = LegacyCheckDefinition(
    check_function=check_innovaphone_mem,
    discovery_function=inventory_innovaphone_mem,
    service_name="Memory",
    check_ruleset_name="innovaphone_mem",
)
