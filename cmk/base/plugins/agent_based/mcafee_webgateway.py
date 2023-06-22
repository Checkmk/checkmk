#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
import typing

from cmk.base.plugins.agent_based.agent_based_api import v1
from cmk.base.plugins.agent_based.utils import mcafee_gateway


class Section(typing.NamedTuple):
    infections: int | None = None
    connections_blocked: int | None = None


class Params(typing.TypedDict, total=False):
    infections: tuple[float, float]
    connections_blocked: tuple[float, float]


ValueStore = typing.MutableMapping[str, typing.Any]


def discover_mcafee_gateway(section: Section) -> v1.type_defs.DiscoveryResult:
    yield v1.Service()


def parse_mcaffee_webgateway(string_table: v1.type_defs.StringTable) -> Section | None:
    if not string_table:
        return None
    infections, connections_blocked = [int(x) if x.isdigit() else None for x in string_table[0]]
    return Section(infections=infections, connections_blocked=connections_blocked)


def check_mcafee_webgateway(params: Params, section: Section) -> v1.type_defs.CheckResult:
    yield from _check_mcafee_webgateway(time.time(), v1.get_value_store(), params, section)


def _check_mcafee_webgateway(
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
    detect=mcafee_gateway.DETECT_WEB_GATEWAY,
    parse_function=parse_mcaffee_webgateway,
    fetch=v1.SNMPTree(
        base=".1.3.6.1.4.1.1230.2.7.2.1",
        oids=[
            "2",  # MCAFEE-MWG-MIB::stMalwareDetected.0
            "5",  # MCAFEE-MWG-MIB::stConnectionsBlocked.0
        ],
    ),
)

v1.register.check_plugin(
    name="mcafee_webgateway",
    discovery_function=discover_mcafee_gateway,
    check_function=check_mcafee_webgateway,
    service_name="Web gateway statistics",
    check_ruleset_name="mcafee_web_gateway",
    check_default_parameters=Params(),
)
