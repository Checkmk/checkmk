#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.wmi import inventory_wmi_table_total, wmi_yield_raw_persec

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.plugins.windows.agent_based.libwmi import parse_wmi_table

check_info = {}


def discover_msexch_availability(parsed):
    return inventory_wmi_table_total(parsed)


def check_msexch_availability(item, params, parsed):
    yield from wmi_yield_raw_persec(
        parsed[""],
        item,
        "AvailabilityRequestssec",
        infoname="Requests/sec",
        perfvar="requests_per_sec",
    )


check_info["msexch_availability"] = LegacyCheckDefinition(
    name="msexch_availability",
    parse_function=parse_wmi_table,
    service_name="Exchange Availability Service",
    discovery_function=discover_msexch_availability,
    check_function=check_msexch_availability,
)
