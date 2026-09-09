#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import MutableMapping, Sequence
from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    LevelsT,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.f5_bigip.lib import F5_BIGIP

_NO_LEVELS: LevelsT[int] = ("no_levels", None)


class ConnsParams(TypedDict, total=False):
    conns: LevelsT[int]
    ssl_conns: LevelsT[int]
    connections_rate: LevelsT[int]
    connections_rate_lower: LevelsT[int]
    http_req_rate: LevelsT[int]


@dataclass(frozen=True)
class ConnectionStats:
    connections: int | None
    ssl_connections: int | None
    native_connections: int | None
    compat_connections: int | None
    http_requests: int | None


Section = Sequence[ConnectionStats]


def _optional_counter(value: str) -> int | None:
    """Return the counter, or None if the device does not answer this OID.

    cmk.checkengine.snmplib fills the columns of an SNMP tree the device does not answer
    with empty strings. Every other value comes from the device, and all of the OIDs
    fetched here are counters or gauges, so it has to be a number: one that is present but
    not numeric means the device violated the MIB, and a crash report is more useful than
    silently reporting nothing.
    """
    return int(value) if value else None


def parse_f5_bigip_conns(string_table: StringTable) -> Section:
    return [
        ConnectionStats(
            connections=_optional_counter(connections),
            ssl_connections=_optional_counter(ssl_connections),
            native_connections=_optional_counter(native),
            compat_connections=_optional_counter(compat),
            http_requests=_optional_counter(http_requests),
        )
        for connections, ssl_connections, native, compat, http_requests in string_table
    ]


def discover_f5_bigip_conns(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def _counter_rate(
    value_store: MutableMapping[str, object],
    key: str,
    now: float,
    counter: int | None,
) -> float:
    if counter is None:
        return 0.0
    return get_rate(value_store, key, now, counter, raise_overflow=True)


def check_f5_bigip_conns(params: ConnsParams, section: Section) -> CheckResult:
    value_store = get_value_store()
    now = time.time()

    connections: int | None = None
    ssl_connections: int | None = None
    connection_rate = 0.0
    http_request_rate: float | None = None

    for stats in section:
        connection_rate += _counter_rate(value_store, "native", now, stats.native_connections)
        connection_rate += _counter_rate(value_store, "compat", now, stats.compat_connections)

        http_request_rate = (
            get_rate(value_store, "stathttpreqs", now, stats.http_requests, raise_overflow=True)
            if stats.http_requests is not None
            else None
        )

        if stats.connections is not None:
            connections = (connections or 0) + stats.connections
        if stats.ssl_connections is not None:
            ssl_connections = (ssl_connections or 0) + stats.ssl_connections

    for value, levels_upper, levels_lower, metric_name, label in (
        (connections, params.get("conns"), None, "connections", "Connections"),
        (ssl_connections, params.get("ssl_conns"), None, "connections_ssl", "SSL connections"),
        (
            connection_rate,
            params.get("connections_rate"),
            params.get("connections_rate_lower"),
            "connections_rate",
            "Connections/s",
        ),
        (
            http_request_rate,
            params.get("http_req_rate"),
            None,
            "requests_per_second",
            "HTTP requests/s",
        ),
    ):
        # SSL may not be configured, eg. on test servers
        if value is None:
            yield Result(state=State.OK, summary=f"{label}: not configured")
            continue

        yield from check_levels(
            value,
            levels_upper=levels_upper or _NO_LEVELS,
            levels_lower=levels_lower or _NO_LEVELS,
            metric_name=metric_name,
            label=label,
        )


snmp_section_f5_bigip_conns = SimpleSNMPSection(
    name="f5_bigip_conns",
    detect=F5_BIGIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3375.2.1.1.2",
        oids=[
            "1.8",  # F5-BIGIP-SYSTEM-MIB::sysStatClientCurConns
            "9.2",  # F5-BIGIP-SYSTEM-MIB::sysClientsslStatCurConns
            "9.6",  # F5-BIGIP-SYSTEM-MIB::sysClientsslStatTotNativeConns
            "9.9",  # F5-BIGIP-SYSTEM-MIB::sysClientsslStatTotCompatConns
            "1.56",  # F5-BIGIP-SYSTEM-MIB::sysStatHttpRequests
        ],
    ),
    parse_function=parse_f5_bigip_conns,
)


check_plugin_f5_bigip_conns = CheckPlugin(
    name="f5_bigip_conns",
    service_name="Open Connections",
    discovery_function=discover_f5_bigip_conns,
    check_function=check_f5_bigip_conns,
    check_ruleset_name="f5_connections",
    check_default_parameters=ConnsParams(
        conns=("fixed", (25000, 30000)),
        ssl_conns=("fixed", (25000, 30000)),
        http_req_rate=("fixed", (500, 1000)),
    ),
)
