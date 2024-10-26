#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Cisco Prime access point check
see https://solutionpartner.cisco.com/media/prime-infrastructure/api-reference/
      szier-m8-106.cisco.com/webacs/api/v1/data/AccessPointscc3b.html
"""

import collections
from collections.abc import Iterable, Mapping

from cmk.base.check_legacy_includes.cisco_prime import parse_cisco_prime

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render, StringTable

check_info = {}

Section = Mapping


def parse_cisco_prime_wifi_access_points(string_table: StringTable) -> Section:
    return parse_cisco_prime("accessPointsDTO", string_table)


def discover_cisco_prime_wifi_access_points(section: Section) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


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
        human_readable_func=render.percent,
        infoname="Percent Critical",
    )
    for k, v in counts.items():
        yield 0, f"{k.title()}: {v!r}", [("ap_devices_%s" % k.lower(), v)]


check_info["cisco_prime_wifi_access_points"] = LegacyCheckDefinition(
    name="cisco_prime_wifi_access_points",
    parse_function=parse_cisco_prime_wifi_access_points,
    service_name="Cisco Prime WiFi Access Points",
    discovery_function=discover_cisco_prime_wifi_access_points,
    check_function=check_cisco_prime_wifi_access_points,
    check_ruleset_name="cisco_prime_wifi_access_points",
    check_default_parameters={
        "levels": (20.0, 40.0),
    },
)
