#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

from cmk.base.check_api import contains, LegacyCheckDefinition
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

factory_settings["avaya_45xx_cpu_default_levels"] = {"levels": (90.0, 95.0)}


def inventory_avaya_45xx_cpu(info):
    for idx, _line in enumerate(info):
        yield str(idx), {}


def check_avaya_45xx_cpu(item, params, info):
    now = time.time()
    for idx, used_perc in enumerate(info):
        if str(idx) == item:
            return check_cpu_util(int(used_perc[0]), params, now)
    return None


check_info["avaya_45xx_cpu"] = LegacyCheckDefinition(
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.45.3"),
    check_function=check_avaya_45xx_cpu,
    discovery_function=inventory_avaya_45xx_cpu,
    service_name="CPU utilization CPU %s",
    check_ruleset_name="cpu_utilization_multiitem",
    default_levels_variable="avaya_45xx_cpu_default_levels",
    # S5-CHASSIS-MIB
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.45.1.6.3.8.1.1.5",
        oids=["3"],
    ),
    check_default_parameters={"levels": (90.0, 95.0)},
)
