#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import CheckPlugin
from cmk.plugins.lib.ups import check_ups_battery_state, discover_ups_battery_state

check_plugin_ups_battery_state = CheckPlugin(
    name="ups_battery_state",
    sections=["ups_battery_warnings", "ups_on_battery", "ups_seconds_on_battery"],
    service_name="Battery state",
    check_function=check_ups_battery_state,
    discovery_function=discover_ups_battery_state,
)
