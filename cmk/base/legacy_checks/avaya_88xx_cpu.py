#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.avaya import DETECT_AVAYA

factory_settings["avaya_88xx_cpu_default_levels"] = {"util": (90.0, 95.0)}


def inventory_avaya_88xx_cpu(info):
    return [(None, {})]


def check_avaya_88xx_cpu(_no_item, params, info):
    if not info:
        return None
    return check_cpu_util(int(info[0][0]), params, time.time())


check_info["avaya_88xx_cpu"] = LegacyCheckDefinition(
    detect=DETECT_AVAYA,
    check_function=check_avaya_88xx_cpu,
    discovery_function=inventory_avaya_88xx_cpu,
    service_name="CPU utilization",
    default_levels_variable="avaya_88xx_cpu_default_levels",
    check_ruleset_name="cpu_utilization",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2272.1.1",
        oids=["20"],
    ),
)
