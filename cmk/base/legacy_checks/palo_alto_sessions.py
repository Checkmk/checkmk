#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.palo_alto.lib import DETECT_PALO_ALTO

check_info = {}


def discover_palo_alto_sessions(info):
    return [(None, None)]


def check_palo_alto_sessions(_no_item, params, info):
    sessions_supported, total, tcp, udp, icmp, sslproxy = map(int, info[0])

    if sessions_supported == 0:
        sessions_used_perc = 0.0
    else:
        sessions_used_perc = float(total) * 100 / sessions_supported

    infotext = "%d total active sessions: %d TCP, %d UDP, %d ICMP, %d SSL Proxy." % (
        total,
        tcp,
        udp,
        icmp,
        sslproxy,
    )
    infotext += " %.1f%% of %d supported sessions in use." % (
        sessions_used_perc,
        sessions_supported,
    )

    warn, crit = params["levels_sessions_used"]
    levelstext = " (warn/crit at %d/%d%%)" % (warn, crit)

    perfdata = [
        ("total_active_sessions", total),
        ("tcp_active_sessions", tcp),
        ("udp_active_sessions", udp),
        ("icmp_active_sessions", icmp),
        ("sslproxy_active_sessions", sslproxy),
    ]

    if sessions_used_perc >= crit:
        status = 2
    elif sessions_used_perc >= warn:
        status = 1
    else:
        status = 0

    if status:
        infotext += levelstext

    return status, infotext, perfdata


def parse_palo_alto_sessions(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["palo_alto_sessions"] = LegacyCheckDefinition(
    name="palo_alto_sessions",
    parse_function=parse_palo_alto_sessions,
    detect=DETECT_PALO_ALTO,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25461.2.1.2.3",
        oids=["2", "3", "4", "5", "6", "7"],
    ),
    service_name="Palo Alto Sessions",
    discovery_function=discover_palo_alto_sessions,
    check_function=check_palo_alto_sessions,
    check_ruleset_name="palo_alto_sessions",
    check_default_parameters={
        "levels_sessions_used": (60, 70),
    },
)
