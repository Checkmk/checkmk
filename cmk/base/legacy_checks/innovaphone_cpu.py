#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import saveint
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.config import check_info, factory_settings

factory_settings["innovaphone_cpu_default_levels"] = {"util": (90.0, 95.0)}


def inventory_innovaphone_cpu(info):
    yield None, {}


def check_innovaphone_cpu(_no_item, params, info):
    usage = saveint(info[0][1])
    return check_cpu_util(usage, params)


check_info["innovaphone_cpu"] = {
    "check_function": check_innovaphone_cpu,
    "discovery_function": inventory_innovaphone_cpu,
    "service_name": "CPU utilization",
    "check_ruleset_name": "cpu_utilization",
    "default_levels_variable": "innovaphone_cpu_default_levels",
}
