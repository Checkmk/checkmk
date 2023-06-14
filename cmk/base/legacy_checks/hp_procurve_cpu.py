#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import any_of, contains, SNMPTree

hp_procurve_cpu_default_levels = (80.0, 90.0)


def inventory_hp_procurve_cpu(info):
    if len(info) == 1 and 0 <= int(info[0][0]) <= 100:
        return [(None, hp_procurve_cpu_default_levels)]
    return []


def check_hp_procurve_cpu(item, params, info):
    try:
        util = int(info[0][0])
    except (IndexError, ValueError):
        return None

    if 0 <= util <= 100:
        return check_cpu_util(util, params)
    return None


check_info["hp_procurve_cpu"] = LegacyCheckDefinition(
    detect=any_of(
        contains(".1.3.6.1.2.1.1.2.0", ".11.2.3.7.11"),
        contains(".1.3.6.1.2.1.1.2.0", ".11.2.3.7.8"),
    ),
    check_function=check_hp_procurve_cpu,
    discovery_function=inventory_hp_procurve_cpu,
    service_name="CPU utilization",
    check_ruleset_name="cpu_utilization",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11.2.14.11.5.1.9.6",
        oids=["1"],
    ),
)
