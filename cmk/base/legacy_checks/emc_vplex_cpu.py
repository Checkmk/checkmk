#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.emc import DETECT_VPLEX

emc_vplex_cpu_default_levels = (90.0, 95.0)


def inventory_emc_vplex_cpu(info):
    for director, _util in info:
        yield director, emc_vplex_cpu_default_levels


def check_emc_vplex_cpu(item, params, info):
    for director, util in info:
        if director == item:
            return check_cpu_util(max(100 - int(util), 0), params)
    return None


check_info["emc_vplex_cpu"] = LegacyCheckDefinition(
    detect=DETECT_VPLEX,
    check_function=check_emc_vplex_cpu,
    discovery_function=inventory_emc_vplex_cpu,
    service_name="CPU Utilization %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1139.21.2.2",
        oids=["1.1.3", "3.1.1"],
    ),
    check_ruleset_name="cpu_utilization_multiitem",
)
