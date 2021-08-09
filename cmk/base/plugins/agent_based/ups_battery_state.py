#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package

from .agent_based_api.v1 import register
from .utils.ups import check_ups_battery_state, discover_ups_battery_state

register.check_plugin(
    name="ups_battery_state",
    sections=["ups_battery_warnings", "ups_on_battery", "ups_seconds_on_battery"],
    service_name="Battery state",
    check_function=check_ups_battery_state,
    discovery_function=discover_ups_battery_state,
)
