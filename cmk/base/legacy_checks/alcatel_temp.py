#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.alcatel import (
    ALCATEL_TEMP_CHECK_DEFAULT_PARAMETERS,
    inventory_alcatel_temp,
)
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.alcatel import DETECT_ALCATEL


def check_alcatel_temp(item, params, info):
    if len(info) == 1:
        slot_index = 0
    else:
        slot = int(item.split()[1])
        slot_index = slot - 1
    sensor = item.split()[-1]
    items = {"Board": 0, "CPU": 1}
    try:
        # If multiple switches are staked and one of them are
        # not reachable, prevent a exception
        temp_celsius = int(info[slot_index][items[sensor]])
    except Exception:
        return 3, "Sensor not found"
    return check_temperature(temp_celsius, params, "alcatel_temp_%s" % item)


factory_settings["alcatel_temp"] = ALCATEL_TEMP_CHECK_DEFAULT_PARAMETERS


check_info["alcatel_temp"] = LegacyCheckDefinition(
    detect=DETECT_ALCATEL,
    check_function=check_alcatel_temp,
    discovery_function=inventory_alcatel_temp,
    service_name="Temperature %s",
    check_ruleset_name="temperature",
    default_levels_variable="alcatel_temp",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6486.800.1.1.1.3.1.1.3.1",
        oids=["4", "5"],
    ),
    check_default_parameters=ALCATEL_TEMP_CHECK_DEFAULT_PARAMETERS,
)
