#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.barracuda import DETECT_BARRACUDA

# .1.3.6.1.4.1.20632.2.13 3

# Suggested by customer
factory_settings["barracuda_system_cpu_util_default_levels"] = {"util": (80.0, 90.0)}


def inventory_barracuda_system_cpu_util(info):
    yield None, {}


def check_barracuda_system_cpu_util(_no_item, params, info):
    return check_cpu_util(int(info[0][0]), params)


check_info["barracuda_system_cpu_util"] = {
    "detect": DETECT_BARRACUDA,
    "discovery_function": inventory_barracuda_system_cpu_util,
    "check_function": check_barracuda_system_cpu_util,
    "service_name": "CPU utilization",
    # The barracuda spam firewall does not response or returns a timeout error
    # executing 'snmpwalk' on whole tables. But we can workaround here specifying
    # all needed OIDs. Then we can use 'snmpget' and 'snmpwalk' on these single OIDs.
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.20632.2",
        oids=["13"],
    ),
    "check_ruleset_name": "cpu_utilization",
    "default_levels_variable": "barracuda_system_cpu_util_default_levels",
}
