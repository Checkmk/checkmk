#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

from cmk.plugins.lib.bvip import DETECT_BVIP

bvip_util_default_levels = (90, 95)


def inventory_bvip_util(info):
    if info:
        for name in ["Total", "Coder", "VCA"]:
            yield name, bvip_util_default_levels


def check_bvip_util(item, params, info):
    items = {
        "Total": 0,
        "Coder": 1,
        "VCA": 2,
    }

    usage = int(info[0][items[item]])
    if item == "Total":
        usage = 100 - usage
    return check_cpu_util(usage, params)


check_info["bvip_util"] = LegacyCheckDefinition(
    detect=DETECT_BVIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3967.1.1.9.1",
        oids=["1", "2", "3"],
    ),
    service_name="CPU utilization %s",
    discovery_function=inventory_bvip_util,
    check_function=check_bvip_util,
    check_ruleset_name="cpu_utilization_multiitem",
)
