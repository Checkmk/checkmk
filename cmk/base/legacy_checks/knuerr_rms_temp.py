#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.knuerr import DETECT_KNUERR

factory_settings["knuerr_rms_temp_default_levels"] = {
    "levels": (30.0, 35.0),
}


def inventory_knuerr_rms_temp(info):
    return [("Ambient", {})]


def check_knuerr_rms_temp(_no_item, params, info):
    return check_temperature(float(info[0][0]) / 10, params, "knuerr_rms_temp")


check_info["knuerr_rms_temp"] = {
    "detect": DETECT_KNUERR,
    "default_levels_variable": "knuerr_rms_temp_default_levels",
    "check_function": check_knuerr_rms_temp,
    "discovery_function": inventory_knuerr_rms_temp,
    "service_name": "Temperature %s",
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.3711.15.1.1.1.1",
        oids=["4"],
    ),
    "check_ruleset_name": "temperature",
}
