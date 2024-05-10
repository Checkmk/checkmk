#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util_unix, CPUInfo
from cmk.base.config import check_info

from cmk.agent_based.v2 import StringTable


def inventory_statgrab_cpu(info):
    if len(info) > 1:
        return [(None, {})]
    return []


def check_statgrab_cpu(_no_item, params, info):
    if not params:
        params = {}

    user = 0
    nice = 0
    system = 0
    idle = 0
    iowait = 0
    for var, value in info:
        if var == "user":
            user = int(value)
        elif var == "nice":
            nice = int(value)
        elif var == "kernel":
            system = int(value)
        elif var == "idle":
            idle = int(value)
        elif var == "iowait":
            iowait = int(value)

    values = CPUInfo("cpu", user, nice, system, idle, iowait)

    return check_cpu_util_unix(values, params)


def parse_statgrab_cpu(string_table: StringTable) -> StringTable:
    return string_table


check_info["statgrab_cpu"] = LegacyCheckDefinition(
    parse_function=parse_statgrab_cpu,
    service_name="CPU utilization",
    discovery_function=inventory_statgrab_cpu,
    check_function=check_statgrab_cpu,
    check_ruleset_name="cpu_iowait",
)
