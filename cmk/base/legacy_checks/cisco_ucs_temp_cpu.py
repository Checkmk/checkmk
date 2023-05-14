#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.cisco_ucs import DETECT
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

# comNET GmbH, Fabian Binder - 2018-05-30

# .1.3.6.1.4.1.9.9.719.1.41.2.1.2  cpu Unit Name
# .1.3.6.1.4.1.9.9.719.1.41.2.1.10 cucsProcessorEnvStatsTemperature

factory_settings["cisco_ucs_temp_cpu_default_levels"] = {
    "levels": (75.0, 85.0),
}


def inventory_cisco_ucs_temp_cpu(info):
    for name, _value in info:
        name = name.split("/")[3]
        yield name, {}


def check_cisco_ucs_temp_cpu(item, params, info):
    for name, value in info:
        name = name.split("/")[3]
        if name == item:
            temp = int(value)
            return check_temperature(temp, params, "cisco_temp_%s" % item)
    return None


check_info["cisco_ucs_temp_cpu"] = LegacyCheckDefinition(
    detect=DETECT,
    discovery_function=inventory_cisco_ucs_temp_cpu,
    check_function=check_cisco_ucs_temp_cpu,
    service_name="Temperature CPU %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.719.1.41.2.1",
        oids=["2", "10"],
    ),
    check_ruleset_name="temperature",
    default_levels_variable="cisco_ucs_temp_cpu_default_levels",
)
