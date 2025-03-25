#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="arg-type"

from cmk.base.check_legacy_includes.wmi import (
    inventory_wmi_table_total,
    parse_wmi_table,
    wmi_yield_raw_persec,
)

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}


def discover_msexch_autodiscovery(parsed):
    return inventory_wmi_table_total(parsed)


def check_msexch_autodiscovery(_no_item, params, parsed):
    yield from wmi_yield_raw_persec(
        parsed[""], None, "RequestsPersec", infoname="Requests/sec", perfvar="requests_per_sec"
    )


check_info["msexch_autodiscovery"] = LegacyCheckDefinition(
    name="msexch_autodiscovery",
    parse_function=parse_wmi_table,
    service_name="Exchange Autodiscovery",
    discovery_function=discover_msexch_autodiscovery,
    check_function=check_msexch_autodiscovery,
)
