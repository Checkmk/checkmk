#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)

Section = tuple[int, int]


def parse_juniper_trpz_aps(string_table: Sequence[StringTable]) -> Section | None:
    """
    >>> parse_juniper_trpz_aps([[['1', '0']]])
    (1, 0)
    """
    return (int(string_table[0][0][0]), int(string_table[0][0][1])) if string_table[0] else None


def discovery_juniper_trpz_aps(section: Section) -> DiscoveryResult:
    yield Service()


def _check_common_juniper_trpz_aps(node_name: str, section: Section) -> CheckResult:
    yield Result(
        state=State.OK,
        summary="%sOnline access points: %d, Sessions: %d"
        % (node_name and "[%s] " % node_name, section[0], section[1]),
    )


def check_juniper_trpz_aps(section: Section) -> CheckResult:
    """
    >>> for result in check_juniper_trpz_aps((1, 0)):
    ...   print(result)
    Metric('ap_devices_total', 1.0)
    Metric('total_sessions', 0.0)
    Result(state=<State.OK: 0>, summary='Online access points: 1, Sessions: 0')
    """
    yield Metric("ap_devices_total", section[0])
    yield Metric("total_sessions", section[1])
    yield from _check_common_juniper_trpz_aps("", section)


def cluster_check_juniper_trpz_aps(section: Mapping[str, Section | None]) -> CheckResult:
    """
    >>> for result in cluster_check_juniper_trpz_aps({"node1": (1, 2), "node2": (3, 4)}):
    ...   print(result)
    Result(state=<State.OK: 0>, summary='Total: 4 access points, Sessions: 6')
    Metric('ap_devices_total', 4.0)
    Metric('total_sessions', 6.0)
    Result(state=<State.OK: 0>, summary='[node1] Online access points: 1, Sessions: 2')
    Result(state=<State.OK: 0>, summary='[node2] Online access points: 3, Sessions: 4')
    """
    total_aps = sum(n[0] for n in section.values() if n)
    total_sessions = sum(n[1] for n in section.values() if n)

    if len(section) > 1:
        yield Result(
            state=State.OK,
            summary="Total: %d access points, Sessions: %d" % (total_aps, total_sessions),
        )
    yield Metric("ap_devices_total", total_aps)
    yield Metric("total_sessions", total_sessions)

    for node_name, node_section in section.items():
        if node_section is not None:
            yield from _check_common_juniper_trpz_aps(node_name, node_section)


snmp_section_juniper_trpz_aps = SNMPSection(
    name="juniper_trpz_aps",
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.14525.3.1"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.14525.3.3"),
    ),
    parse_function=parse_juniper_trpz_aps,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.14525.4",
            oids=[
                "5.1.1.1",  # number of active access points
                "4.1.1.4",  # number of sessions on active access points
            ],
        ),
    ],
)

check_plugin_juniper_trpz_aps = CheckPlugin(
    name="juniper_trpz_aps",
    service_name="Access Points",
    discovery_function=discovery_juniper_trpz_aps,
    check_function=check_juniper_trpz_aps,
    cluster_check_function=cluster_check_juniper_trpz_aps,
)
