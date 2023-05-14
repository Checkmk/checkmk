#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, SNMPTree
from cmk.base.plugins.agent_based.utils.enterasys import DETECT_ENTERASYS

factory_settings["enterasys_cpu_default_levels"] = {
    "levels": (90.0, 95.0),
}


def inventory_enterasys_cpu_util(info):
    # [:-2] to remove the oid end
    return [(x[0][:-2], {}) for x in info]


def check_enterasys_cpu_util(item, params, info):
    for core, util in info:
        if item == core[:-2]:
            usage = int(util) / 10.0
            return check_cpu_util(usage, params)
    return None


check_info["enterasys_cpu_util"] = LegacyCheckDefinition(
    detect=DETECT_ENTERASYS,
    check_function=check_enterasys_cpu_util,
    discovery_function=inventory_enterasys_cpu_util,
    service_name="CPU util %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5624.1.2.49.1.1.1.1",
        oids=[OIDEnd(), "3"],
    ),
    check_ruleset_name="cpu_utilization_multiitem",
    default_levels_variable="enterasys_cpu_default_levels",
)
