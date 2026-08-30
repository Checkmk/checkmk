#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.palo_alto.lib import DETECT_PALO_ALTO


def discover_palo_alto_sessions(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_palo_alto_sessions(
    params: Mapping[str, tuple[int, int]], section: StringTable
) -> CheckResult:
    sessions_supported, total, tcp, udp, icmp, sslproxy = map(int, section[0])

    sessions_used_perc = 0.0 if sessions_supported == 0 else float(total) * 100 / sessions_supported

    infotext = (
        f"{total} total active sessions: {tcp} TCP, {udp} UDP, {icmp} ICMP, {sslproxy} SSL Proxy."
    )
    infotext += f" {sessions_used_perc:.1f}% of {sessions_supported} supported sessions in use."

    warn, crit = params["levels_sessions_used"]

    if sessions_used_perc >= crit:
        state = State.CRIT
    elif sessions_used_perc >= warn:
        state = State.WARN
    else:
        state = State.OK

    if state is not State.OK:
        infotext += f" (warn/crit at {warn}/{crit}%)"

    yield Result(state=state, summary=infotext)
    yield Metric("total_active_sessions", total)
    yield Metric("tcp_active_sessions", tcp)
    yield Metric("udp_active_sessions", udp)
    yield Metric("icmp_active_sessions", icmp)
    yield Metric("sslproxy_active_sessions", sslproxy)


def parse_palo_alto_sessions(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_palo_alto_sessions = SimpleSNMPSection(
    name="palo_alto_sessions",
    parse_function=parse_palo_alto_sessions,
    detect=DETECT_PALO_ALTO,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25461.2.1.2.3",
        oids=["2", "3", "4", "5", "6", "7"],
    ),
)


check_plugin_palo_alto_sessions = CheckPlugin(
    name="palo_alto_sessions",
    service_name="Palo Alto Sessions",
    discovery_function=discover_palo_alto_sessions,
    check_function=check_palo_alto_sessions,
    check_ruleset_name="palo_alto_sessions",
    check_default_parameters={
        "levels_sessions_used": (60, 70),
    },
)
