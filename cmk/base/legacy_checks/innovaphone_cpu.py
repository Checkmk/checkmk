#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition, saveint
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.config import check_info


def inventory_innovaphone_cpu(info):
    yield None, {}


def check_innovaphone_cpu(_no_item, params, info):
    usage = saveint(info[0][1])
    return check_cpu_util(usage, params)


check_info["innovaphone_cpu"] = LegacyCheckDefinition(
    service_name="CPU utilization",
    discovery_function=inventory_innovaphone_cpu,
    check_function=check_innovaphone_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (90.0, 95.0)},
)
