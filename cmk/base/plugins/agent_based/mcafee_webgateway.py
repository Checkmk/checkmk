#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
The McAfee Web Gateway has been rebranded to Skyhigh Secure Web Gateway with its release 12.2.2.
Where possibile the "McAfee" string has been removed in favor of more generic therms.
The old plug-in names, value_store dict keys, and ruleset names have been kept for compatibility/history-keeping reasons.
"""
import time
import typing

from cmk.base.plugins.agent_based.agent_based_api import v1

from cmk.plugins.lib import mcafee_gateway


class Section(typing.NamedTuple):
    infections: int | None = None
    connections_blocked: int | None = None


class Params(typing.TypedDict, total=False):
    infections: tuple[float, float]
    connections_blocked: tuple[float, float]


ValueStore = typing.MutableMapping[str, typing.Any]


def discover_webgateway(section: Section) -> v1.type_defs.DiscoveryResult:
    yield v1.Service()


def parse_webgateway(string_table: v1.type_defs.StringTable) -> Section | None:
    if not string_table:
        return None
    infections, connections_blocked = (int(x) if x.isdigit() else None for x in string_table[0])
    return Section(infections=infections, connections_blocked=connections_blocked)


def check_webgateway(params: Params, section: Section) -> v1.type_defs.CheckResult:
    yield from _check_webgateway(time.time(), v1.get_value_store(), params, section)


def _check_webgateway(
    now: float, value_store: ValueStore, params: Params, section: Section
) -> v1.type_defs.CheckResult:
    yield from mcafee_gateway.compute_rate(
        now=now,
        value_store=value_store,
        value=section.infections,
        metric_name="infections_rate",
        levels=params.get("infections"),
        key="check_mcafee_webgateway.infections",
        label="Infections",
    )
    yield from mcafee_gateway.compute_rate(
        now=now,
        value_store=value_store,
        value=section.connections_blocked,
        metric_name="connections_blocked_rate",
        levels=params.get("connections_blocked"),
        key="check_mcafee_webgateway.connections_blocked",
        label="Connections blocked",
    )


v1.register.snmp_section(
    name="mcafee_webgateway",
    parsed_section_name="webgateway",
    detect=mcafee_gateway.DETECT_MCAFEE_WEBGATEWAY,
    parse_function=parse_webgateway,
    fetch=v1.SNMPTree(
        base=".1.3.6.1.4.1.1230.2.7.2.1",
        oids=[
            "2",  # MCAFEE-MWG-MIB::stMalwareDetected.0
            "5",  # MCAFEE-MWG-MIB::stConnectionsBlocked.0
        ],
    ),
)

v1.register.snmp_section(
    name="skyhigh_security_webgateway",
    parsed_section_name="webgateway",
    detect=mcafee_gateway.DETECT_SKYHIGH_WEBGATEWAY,
    parse_function=parse_webgateway,
    fetch=v1.SNMPTree(
        base=".1.3.6.1.4.1.59732.2.7.2.1",
        oids=[
            "2",  # ::stMalwareDetected.0
            "5",  # ::stConnectionsBlocked.0
        ],
    ),
)

v1.register.check_plugin(
    name="mcafee_webgateway",
    sections=["webgateway"],
    discovery_function=discover_webgateway,
    check_function=check_webgateway,
    service_name="Web gateway statistics",
    check_ruleset_name="mcafee_web_gateway",
    check_default_parameters=Params(),
)
