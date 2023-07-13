#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.cmciii import (
    check_cmciii_lcp_fanunit,
    inventory_cmciii_lcp_fanunit,
)
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.cmciii import DETECT_CMCIII_LCP

# Note: this check is obsolete, please use cmciii.temp_in_out instead


check_info["cmciii_lcp_airin"] = LegacyCheckDefinition(
    detect=DETECT_CMCIII_LCP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2606.7.4.2.2.1.10.2",
        oids=["6", "13", "15", "23", "21", "20", "19", "18", "17", "7", "8", "9"],
    ),
    service_name="Temperature %s",
    discovery_function=lambda info: inventory_cmciii_lcp_fanunit("Air", "In", info),
    check_function=check_cmciii_lcp_fanunit,
    check_ruleset_name="temperature",
)
#
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.6 Air.Temperature.DescName
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.7 Air.Temperature.In-Top
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.8 Air.Temperature.In-Mid
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.9 Air.Temperature.In-Bot
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.10 Air.Temperature.Out-Top
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.11 Air.Temperature.Out-Mid
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.12 Air.Temperature.Out-Bot
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.13 Air.Temperature.Status
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.14 Air.Temperature.Category
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.15 Air.Server-In.DescName
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.16 Air.Server-In.Setpoint
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.17 Air.Server-In.Average
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.18 Air.Server-In.SetPtHighAlarm
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.19 Air.Server-In.SetPtHighWarning
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.20 Air.Server-In.SetPtLowWarning
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.21 Air.Server-In.SetPtLowAlarm
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.22 Air.Server-In.Hysteresis
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.23 Air.Server-In.Status
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.24 Air.Server-In.Category
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.25 Air.Server-Out.DescName
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.26 Air.Server-Out.Average
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.27 Air.Server-Out.SetPtHighAlarm
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.28 Air.Server-Out.SetPtHighWarning
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.29 Air.Server-Out.SetPtLowWarning
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.30 Air.Server-Out.SetPtLowAlarm
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.31 Air.Server-Out.Hysteresis
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.32 Air.Server-Out.Status
# .1.3.6.1.4.1.2606.7.4.2.2.1.3.2.33 Air.Server-Out.Category
#
