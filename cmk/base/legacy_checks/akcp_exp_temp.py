#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.akcp_sensor import (
    AKCP_TEMP_CHECK_DEFAULT_PARAMETERS,
    check_akcp_sensor_temp,
    inventory_akcp_sensor_temp,
)
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.akcp import DETECT_AKCP_EXP

# Example for contents of info
#           description         degree unit status low_crit low_warn high_warn high_crit degreeraw online
# ["Port 8 Temperatur CL Lager", "20", "C",   "5",   "10",    "20",    "30",     "40",      "0",     1]


factory_settings["akcp_temp_default_levels"] = AKCP_TEMP_CHECK_DEFAULT_PARAMETERS

check_info["akcp_exp_temp"] = LegacyCheckDefinition(
    detect=DETECT_AKCP_EXP,
    check_function=check_akcp_sensor_temp,
    discovery_function=inventory_akcp_sensor_temp,
    service_name="Temperature %s",
    default_levels_variable="akcp_temp_default_levels",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3854.2.3.2.1",
        oids=["2", "4", "5", "6", "9", "10", "11", "12", "19", "8"],
    ),
    check_ruleset_name="temperature",
)
