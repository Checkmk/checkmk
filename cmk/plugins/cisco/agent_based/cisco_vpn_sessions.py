#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# .1.3.6.1.4.1.9.9.392.1.1.1.0 = INTEGER: 150
# .1.3.6.1.4.1.9.9.392.1.3.26.0 = Gauge32: 0
# .1.3.6.1.4.1.9.9.392.1.3.27.0 = Counter32: 0
# .1.3.6.1.4.1.9.9.392.1.3.28.0 = Gauge32: 0
# .1.3.6.1.4.1.9.9.392.1.3.29.0 = Gauge32: 13
# .1.3.6.1.4.1.9.9.392.1.3.30.0 = Counter32: 73624
# .1.3.6.1.4.1.9.9.392.1.3.31.0 = Gauge32: 13
# .1.3.6.1.4.1.9.9.392.1.3.35.0 = Gauge32: 28
# .1.3.6.1.4.1.9.9.392.1.3.36.0 = Counter32: 1590
# .1.3.6.1.4.1.9.9.392.1.3.37.0 = Gauge32: 37
# .1.3.6.1.4.1.9.9.392.1.3.38.0 = Gauge32: 0
# .1.3.6.1.4.1.9.9.392.1.3.39.0 = Counter32: 0
# .1.3.6.1.4.1.9.9.392.1.3.40.0 = Gauge32: 0
#
# CISCO-REMOTE-ACCESS-MONITOR-MIB::crasMaxSessionsSupportable.0 = INTEGER: 150 Sessions
# CISCO-REMOTE-ACCESS-MONITOR-MIB::crasIPSecNumSessions.0 = Gauge32: 0 Sessions
# CISCO-REMOTE-ACCESS-MONITOR-MIB::crasIPSecCumulateSessions.0 = Counter32: 0 Sessions
# CISCO-REMOTE-ACCESS-MONITOR-MIB::crasIPSecPeakConcurrentSessions.0 = Gauge32: 0 Sessions
# CISCO-REMOTE-ACCESS-MONITOR-MIB::crasL2LNumSessions.0 = Gauge32: 13 Sessions
# CISCO-REMOTE-ACCESS-MONITOR-MIB::crasL2LCumulateSessions.0 = Counter32: 73624 Sessions
# CISCO-REMOTE-ACCESS-MONITOR-MIB::crasL2LPeakConcurrentSessions.0 = Gauge32: 13 Sessions
# CISCO-REMOTE-ACCESS-MONITOR-MIB::crasSVCNumSessions.0 = Gauge32: 28 Sessions
# CISCO-REMOTE-ACCESS-MONITOR-MIB::crasSVCCumulateSessions.0 = Counter32: 1590 Sessions
# CISCO-REMOTE-ACCESS-MONITOR-MIB::crasSVCPeakConcurrentSessions.0 = Gauge32: 37 Sessions
# CISCO-REMOTE-ACCESS-MONITOR-MIB::crasWebvpnNumSessions.0 = Gauge32: 0 Sessions
# CISCO-REMOTE-ACCESS-MONITOR-MIB::crasWebvpnCumulateSessions.0 = Counter32: 0 Sessions
# CISCO-REMOTE-ACCESS-MONITOR-MIB::crasWebvpnPeakConcurrentSessions.0 = Gauge32: 0 Sessions


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

SESSION_TYPES = ["IPsec RA", "IPsec L2L", "AnyConnect SVC", "WebVPN"]
METRICS_PER_SESSION_TYPE = ["active_sessions", "cumulative_sessions", "peak_sessions"]

Section = dict[str, dict[str, int]]


def parse_cisco_vpn_sessions(
    string_table: StringTable,
) -> Section | None:
    if not string_table:
        return None

    raw_data = string_table[0]
    parsed = {}
    summary = {"active_sessions": 0, "cumulative_sessions": 0}

    max_sessions = None
    try:
        max_sessions = int(raw_data[-1])
        summary["maximum_sessions"] = max_sessions
    except ValueError:
        pass

    for idx_session_type, session_type in enumerate(SESSION_TYPES):
        try:
            session_metrics = {}
            for idx_metric, metric in enumerate(METRICS_PER_SESSION_TYPE):
                session_metrics[metric] = int(
                    raw_data[idx_session_type * len(METRICS_PER_SESSION_TYPE) + idx_metric]
                )
        except ValueError:
            continue

        if max_sessions is not None:
            session_metrics["maximum_sessions"] = max_sessions

        parsed[session_type] = session_metrics
        summary["active_sessions"] += session_metrics["active_sessions"]
        summary["cumulative_sessions"] += session_metrics["cumulative_sessions"]

    parsed["Summary"] = summary

    return parsed


snmp_section_cisco_vpn_sessions = SimpleSNMPSection(
    name="cisco_vpn_sessions",
    parse_function=parse_cisco_vpn_sessions,
    detect=any_of(
        contains(".1.3.6.1.2.1.1.1.0", "cisco pix security"),
        contains(".1.3.6.1.2.1.1.1.0", "cisco adaptive security"),
        contains(".1.3.6.1.2.1.1.1.0", "cisco firepower threat defense"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.392.1",
        oids=[
            "3.26",  # crasIPSecNumSessions
            "3.27",  # crasIPSecCumulateSessions
            "3.28",  # crasIPSecPeakConcurrentSessions
            "3.29",  # crasL2LNumSessions
            "3.30",  # crasL2LCumulateSessions
            "3.31",  # crasL2LPeakConcurrentSessions
            "3.35",  # crasSVCNumSessions
            "3.36",  # crasSVCCumulateSessions
            "3.37",  # crasSVCPeakConcurrentSessions
            "3.38",  # crasWebvpnNumSessions
            "3.39",  # crasWebvpnCumulateSessions
            "3.40",  # crasWebvpnPeakConcurrentSessions
            "1.1",  # crasMaxSessionsSupportable
        ],
    ),
)


def discover_cisco_vpn_sessions(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_cisco_vpn_sessions(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    yield from check_levels(
        data["active_sessions"],
        "active_sessions",
        params.get("active_sessions"),
        infoname="Active sessions",
        human_readable_func=int,
    )

    if item != "Summary":
        yield from check_levels(
            data["peak_sessions"],
            "active_sessions_peak",
            None,
            infoname="Peak count",
            human_readable_func=int,
        )

    if "maximum_sessions" in data:
        yield Result(state=State.OK, summary=f"Overall system maximum: {data['maximum_sessions']}")

    yield Result(state=State.OK, summary=f"Cumulative count: {data['cumulative_sessions']}")


check_plugin_cisco_vpn_sessions = CheckPlugin(
    name="cisco_vpn_sessions",
    service_name="VPN Sessions %s",
    discovery_function=discover_cisco_vpn_sessions,
    check_function=check_cisco_vpn_sessions,
    check_ruleset_name="cisco_vpn_sessions",
    check_default_parameters={},
)
