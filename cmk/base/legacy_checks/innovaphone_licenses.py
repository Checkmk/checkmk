#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import DiscoveryResult, Service, StringTable

check_info = {}


def savefloat(f: str) -> float:
    """Tries to cast a string to an float and return it. In case this fails,
    it returns 0.0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0.0 back from this function,
    you can not know whether it is really 0.0 or something went wrong."""
    try:
        return float(f)
    except (TypeError, ValueError):
        return 0.0


def discover_innovaphone_licenses(string_table: StringTable) -> DiscoveryResult:
    if string_table:
        yield Service()


def check_innovaphone_licenses(_no_item, params, info):
    if not info:
        return None
    total, used = map(savefloat, info[0])
    perc_used = (100.0 * used) / total
    warn, crit = params["levels"]
    message = f"Used {used:.0f}/{total:.0f} Licences ({perc_used:.0f}%)"
    levels = f"Warning/ Critical at ({warn}/{crit})"
    perf = [("licenses", used, None, None, total)]
    if perc_used > crit:
        return 2, message + levels, perf
    if perc_used > warn:
        return 1, message + levels, perf
    return 0, message, perf


def parse_innovaphone_licenses(string_table: StringTable) -> StringTable:
    return string_table


check_info["innovaphone_licenses"] = LegacyCheckDefinition(
    name="innovaphone_licenses",
    parse_function=parse_innovaphone_licenses,
    service_name="Licenses",
    discovery_function=discover_innovaphone_licenses,
    check_function=check_innovaphone_licenses,
    check_default_parameters={
        "levels": (90.0, 95.0),
    },
)
