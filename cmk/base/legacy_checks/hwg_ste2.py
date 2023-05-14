#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import contains, LegacyCheckDefinition
from cmk.base.check_legacy_includes.hwg import (
    check_hwg_humidity,
    check_hwg_temp,
    HWG_HUMIDITY_DEFAULTLEVELS,
    HWG_TEMP_DEFAULTLEVELS,
    inventory_hwg_humidity,
    inventory_hwg_temp,
    parse_hwg,
)
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

factory_settings["hwg_humidity_defaultlevels"] = HWG_HUMIDITY_DEFAULTLEVELS


factory_settings["hwg_temp_defaultlevels"] = HWG_TEMP_DEFAULTLEVELS


check_info["hwg_ste2"] = LegacyCheckDefinition(
    detect=contains(".1.3.6.1.2.1.1.1.0", "STE2"),
    parse_function=parse_hwg,
    check_function=check_hwg_temp,
    discovery_function=inventory_hwg_temp,
    service_name="Temperature %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.21796.4.9.3.1",
        oids=["1", "2", "3", "4", "7"],
    ),
    check_ruleset_name="temperature",
    default_levels_variable="hwg_temp_defaultlevels",
)


check_info["hwg_ste2.humidity"] = LegacyCheckDefinition(
    check_function=check_hwg_humidity,
    discovery_function=inventory_hwg_humidity,
    service_name="Humidity %s",
    check_ruleset_name="humidity",
    default_levels_variable="hwg_humidity_defaultlevels",
)
