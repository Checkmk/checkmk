#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.ddn_s2a import parse_ddn_s2a_api_response
from cmk.base.check_legacy_includes.uptime import check_uptime_seconds

check_info = {}


def parse_ddn_s2a_uptime(string_table):
    return {key: value[0] for key, value in parse_ddn_s2a_api_response(string_table).items()}


def inventory_ddn_s2a_uptime(parsed):
    return [(None, {})]


def check_ddn_s2a_uptime(_no_item, params, parsed):
    uptime_years = int(parsed["uptime_years"])
    uptime_days = int(parsed["uptime_days"])
    uptime_hours = int(parsed["uptime_hours"])
    uptime_minutes = int(parsed["uptime_minutes"])

    uptime_sec = 60 * (
        uptime_minutes + 60 * (uptime_hours + 24 * (uptime_days + 365 * uptime_years))
    )
    return check_uptime_seconds(params, uptime_sec)


check_info["ddn_s2a_uptime"] = LegacyCheckDefinition(
    name="ddn_s2a_uptime",
    parse_function=parse_ddn_s2a_uptime,
    service_name="DDN S2A Power-On Time",  # We don't use "Uptime" as a service name here,
    # because this value is different from the uptime value
    # supplied via SNMP.,
    discovery_function=inventory_ddn_s2a_uptime,
    check_function=check_ddn_s2a_uptime,
    check_ruleset_name="uptime",
)
