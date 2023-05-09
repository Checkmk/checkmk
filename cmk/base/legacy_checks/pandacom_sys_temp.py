#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_legacy_includes.pandacom_temp import PANDACOM_TEMP_CHECK_DEFAULT_PARAMETERS
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.pandacom import DETECT_PANDACOM

# .1.3.6.1.4.1.3652.3.1.1.6.0 27

factory_settings["pandacom_temp_default_levels"] = PANDACOM_TEMP_CHECK_DEFAULT_PARAMETERS


def inventory_pandacom_sys_temp(info):
    return [("System", {})]


def check_pandacom_sys_temp(item, params, info):
    return check_temperature(int(info[0][0]), params, "pandacom_sys_%s" % item)


check_info["pandacom_sys_temp"] = {
    "detect": DETECT_PANDACOM,
    "discovery_function": inventory_pandacom_sys_temp,
    "check_function": check_pandacom_sys_temp,
    "service_name": "Temperature %s",
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.3652.3.1.1",
        oids=["6"],
    ),
    "default_levels_variable": "pandacom_temp_default_levels",
    "check_ruleset_name": "temperature",
}
