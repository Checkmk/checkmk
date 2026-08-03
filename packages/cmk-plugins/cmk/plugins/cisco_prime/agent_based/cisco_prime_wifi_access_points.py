#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

"""Cisco Prime access point check
see https://solutionpartner.cisco.com/media/prime-infrastructure/api-reference/
      szier-m8-106.cisco.com/webacs/api/v1/data/AccessPointscc3b.html
"""

import collections
import json
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, Mapping[str, object]]


def parse_cisco_prime_wifi_access_points(string_table: StringTable) -> Section:
    """Parse JSON and return queryResponse/entity entries keyed by "@id".

    See https://solutionpartner.cisco.com/media/prime-infrastructure-api-reference-v3-0/192.168.115.187/webacs/api/v1/data/ClientCountscc3b.html
    """
    elements = json.loads(string_table[0][0])["queryResponse"]["entity"]
    return {elem["accessPointsDTO"]["@id"]: elem["accessPointsDTO"] for elem in elements}


def discover_cisco_prime_wifi_access_points(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_cisco_prime_wifi_access_points(
    params: Mapping[str, Any], section: Section
) -> CheckResult:
    """Sum up all individual counts for each connection type (as well as their sums
    indicated by 'count')"""
    counts = collections.Counter(str(entry["status"]) for entry in section.values())
    count_total, count_critical = len(section), counts["CRITICAL"]
    critical_percent = 100.0 * count_critical / count_total
    yield from check_levels(
        critical_percent,
        "ap_devices_percent_unhealthy",
        params.get("levels", (None, None)),
        human_readable_func=render.percent,
        infoname="Percent Critical",
    )
    for status, count in counts.items():
        yield Result(state=State.OK, summary=f"{status.title()}: {count!r}")
        yield Metric(f"ap_devices_{status.lower()}", count)


agent_section_cisco_prime_wifi_access_points = AgentSection(
    name="cisco_prime_wifi_access_points",
    parse_function=parse_cisco_prime_wifi_access_points,
)


check_plugin_cisco_prime_wifi_access_points = CheckPlugin(
    name="cisco_prime_wifi_access_points",
    service_name="Cisco Prime WiFi Access Points",
    discovery_function=discover_cisco_prime_wifi_access_points,
    check_function=check_cisco_prime_wifi_access_points,
    check_ruleset_name="cisco_prime_wifi_access_points",
    check_default_parameters={
        "levels": (20.0, 40.0),
    },
)
