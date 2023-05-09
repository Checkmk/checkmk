#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.base.plugins.agent_based.utils.pulse_secure as pulse_secure
from cmk.base.check_api import check_levels, discover_single, get_percent_human_readable
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

factory_settings["pulse_secure_disk_util_def_levels"] = {"upper_levels": (80.0, 90.0)}

METRIC_PULSE_SECURE_DISK = "disk_utilization"


def check_pulse_secure_disk_util(item, params, parsed):
    if not parsed:
        return None

    yield check_levels(
        parsed[METRIC_PULSE_SECURE_DISK],
        METRIC_PULSE_SECURE_DISK,
        params.get("upper_levels"),
        infoname="Percentage of disk space used",
        human_readable_func=get_percent_human_readable,
    )
    return None


check_info["pulse_secure_disk_util"] = {
    "detect": pulse_secure.DETECT_PULSE_SECURE,
    "parse_function": lambda info: pulse_secure.parse_pulse_secure(info, METRIC_PULSE_SECURE_DISK),
    "discovery_function": discover_single,
    "check_function": check_pulse_secure_disk_util,
    "service_name": "Pulse Secure disk utilization",
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.12532",
        oids=["25"],
    ),
    "check_ruleset_name": "pulse_secure_disk_util",
    "default_levels_variable": "pulse_secure_disk_util_def_levels",
}
