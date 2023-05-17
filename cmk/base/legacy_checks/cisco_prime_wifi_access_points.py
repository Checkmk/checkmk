#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Cisco Prime access point check
see https://solutionpartner.cisco.com/media/prime-infrastructure/api-reference/
      szier-m8-106.cisco.com/webacs/api/v1/data/AccessPointscc3b.html
"""


import collections

from cmk.base.check_api import (
    check_levels,
    discover_single,
    get_percent_human_readable,
    LegacyCheckDefinition,
)
from cmk.base.check_legacy_includes.cisco_prime import parse_cisco_prime
from cmk.base.config import check_info, factory_settings

factory_settings["cisco_prime_wifi_access_points"] = {
    "levels": (20, 40),
}


def check_cisco_prime_wifi_access_points(item, params, parsed):
    """Sum up all individual counts for each connection type (as well as their sums
    indicated by 'count')"""
    counts = collections.Counter(k["status"] for k in parsed.values())
    count_total, count_critical = len(parsed), counts["CRITICAL"]
    critical_percent = 100.0 * count_critical / count_total
    yield check_levels(
        critical_percent,
        "ap_devices_percent_unhealthy",
        params.get("levels", (None, None)),
        human_readable_func=get_percent_human_readable,
        infoname="Percent Critical",
    )
    for k, v in counts.items():
        yield 0, "%s: %r" % (k.title(), v), [("ap_devices_%s" % k.lower(), v)]


check_info["cisco_prime_wifi_access_points"] = LegacyCheckDefinition(
    parse_function=lambda info: parse_cisco_prime("accessPointsDTO", info),
    discovery_function=discover_single,
    check_function=check_cisco_prime_wifi_access_points,
    default_levels_variable="cisco_prime_wifi_access_points",
    service_name="Cisco Prime WiFi Access Points",
    check_ruleset_name="cisco_prime_wifi_access_points",
    check_default_parameters={
        "levels": (20, 40),
    },
)
