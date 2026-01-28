#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="arg-type"

from collections.abc import Mapping

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition, LegacyCheckResult
from cmk.base.check_legacy_includes.wmi import (
    inventory_wmi_table_total,
    wmi_yield_raw_counter,
    wmi_yield_raw_persec,
)
from cmk.plugins.windows.agent_based.libwmi import parse_wmi_table, WMISection

check_info = {}


def discover_msexch_owa(parsed: WMISection) -> list[tuple[None, dict[str, object]]]:
    return inventory_wmi_table_total(parsed)


def check_msexch_owa(
    _no_item: None, params: Mapping[str, object], parsed: WMISection
) -> LegacyCheckResult:
    table = parsed[""]
    yield from wmi_yield_raw_persec(
        table, None, "RequestsPersec", infoname="Requests/sec", perfvar="requests_per_sec"
    )
    yield from wmi_yield_raw_counter(
        table, None, "CurrentUniqueUsers", infoname="Unique users", perfvar="current_users"
    )


check_info["msexch_owa"] = LegacyCheckDefinition(
    name="msexch_owa",
    parse_function=parse_wmi_table,
    service_name="Exchange OWA",
    discovery_function=discover_msexch_owa,
    check_function=check_msexch_owa,
)
