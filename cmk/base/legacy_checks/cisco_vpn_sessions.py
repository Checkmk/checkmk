#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition

check_info = {}


def check_cisco_vpn_sessions(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    yield check_levels(
        data["active_sessions"],
        "active_sessions",
        params.get("active_sessions"),
        infoname="Active sessions",
        human_readable_func=int,
    )

    if item != "Summary":
        yield check_levels(
            data["peak_sessions"],
            "active_sessions_peak",
            None,
            infoname="Peak count",
            human_readable_func=int,
        )

    if "maximum_sessions" in data:
        yield 0, "Overall system maximum: %s" % data["maximum_sessions"]

    yield 0, "Cumulative count: %s" % data["cumulative_sessions"]


def discover_cisco_vpn_sessions(section):
    yield from ((item, {}) for item in section)


check_info["cisco_vpn_sessions"] = LegacyCheckDefinition(
    name="cisco_vpn_sessions",
    service_name="VPN Sessions %s",
    discovery_function=discover_cisco_vpn_sessions,
    check_function=check_cisco_vpn_sessions,
    check_ruleset_name="cisco_vpn_sessions",
)
