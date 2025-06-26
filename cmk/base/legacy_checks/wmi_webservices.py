#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.wmi import inventory_wmi_table_instances, wmi_yield_raw_counter

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.plugins.windows.agent_based.libwmi import parse_wmi_table

check_info = {}


def check_wmi_webservices(item, params, parsed):
    yield from wmi_yield_raw_counter(
        parsed[""], item, "CurrentConnections", infoname="Connections", perfvar="connections"
    )


def discover_wmi_webservices(p):
    return inventory_wmi_table_instances(p)


check_info["wmi_webservices"] = LegacyCheckDefinition(
    name="wmi_webservices",
    parse_function=parse_wmi_table,
    service_name="Web Service %s",
    discovery_function=discover_wmi_webservices,
    check_function=check_wmi_webservices,
)
