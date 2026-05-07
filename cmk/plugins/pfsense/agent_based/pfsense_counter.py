#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import MutableMapping
from dataclasses import asdict, dataclass
from typing import Any, ReadOnly, TypedDict

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    get_average,
    get_rate,
    get_value_store,
    Metric,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)


@dataclass(frozen=True, kw_only=True)
class PacketCounters:
    matched: int | None = None
    badoffset: int | None = None
    fragment: int | None = None
    short: int | None = None
    normalized: int | None = None
    memdrop: int | None = None


def parse_pfsense_counter(string_table: StringTable) -> PacketCounters | None:
    raw_counters_by_end_oid = dict(string_table)
    counters = PacketCounters(
        matched=_parse_optional_raw_counter(raw_counters_by_end_oid.get("1.0")),
        badoffset=_parse_optional_raw_counter(raw_counters_by_end_oid.get("2.0")),
        fragment=_parse_optional_raw_counter(raw_counters_by_end_oid.get("3.0")),
        short=_parse_optional_raw_counter(raw_counters_by_end_oid.get("4.0")),
        normalized=_parse_optional_raw_counter(raw_counters_by_end_oid.get("5.0")),
        memdrop=_parse_optional_raw_counter(raw_counters_by_end_oid.get("6.0")),
    )
    return counters if any(asdict(counters).values()) else None


def _parse_optional_raw_counter(raw_value: str | None) -> int | None:
    return int(raw_value) if raw_value is not None else None


def discovery_pfsense_counter(section: PacketCounters) -> DiscoveryResult:
    yield Service()


class CheckParameters(TypedDict):
    average: ReadOnly[int]
    badoffset: ReadOnly[tuple[float, float]]
    fragment: ReadOnly[tuple[float, float]]
    short: ReadOnly[tuple[float, float]]
    normalized: ReadOnly[tuple[float, float]]
    memdrop: ReadOnly[tuple[float, float]]


def check_pfsense_counter(params: CheckParameters, section: PacketCounters) -> CheckResult:
    yield from check_pfsense_counter_pure(
        params,
        section,
        time.time(),
        get_value_store(),
    )


def check_pfsense_counter_pure(
    params: CheckParameters,
    section: PacketCounters,
    timestamp: float,
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    backlog_minutes = params["average"]
    yield Result(state=State.OK, summary=f"Values averaged over {backlog_minutes} min")

    yield from _check_counter(
        counter=section.matched,
        backlog_minutes=backlog_minutes,
        timestamp=timestamp,
        value_store=value_store,
        levels=None,
        ident="matched",
        label="Packets that matched a rule",
    )
    yield from _check_counter(
        counter=section.badoffset,
        backlog_minutes=backlog_minutes,
        timestamp=timestamp,
        value_store=value_store,
        levels=params["badoffset"],
        ident="badoffset",
        label="Packets with bad offset",
    )
    yield from _check_counter(
        counter=section.fragment,
        backlog_minutes=backlog_minutes,
        timestamp=timestamp,
        value_store=value_store,
        levels=params["fragment"],
        ident="fragment",
        label="Fragmented packets",
    )
    yield from _check_counter(
        counter=section.short,
        backlog_minutes=backlog_minutes,
        timestamp=timestamp,
        value_store=value_store,
        levels=params["short"],
        ident="short",
        label="Short packets",
    )
    yield from _check_counter(
        counter=section.normalized,
        backlog_minutes=backlog_minutes,
        timestamp=timestamp,
        value_store=value_store,
        levels=params["normalized"],
        ident="normalized",
        label="Normalized packets",
    )
    yield from _check_counter(
        counter=section.memdrop,
        backlog_minutes=backlog_minutes,
        timestamp=timestamp,
        value_store=value_store,
        levels=params["memdrop"],
        ident="memdrop",
        label="Packets dropped due to memory limitations",
    )


def _check_counter(
    *,
    counter: int | None,
    backlog_minutes: int,
    timestamp: float,
    value_store: MutableMapping[str, Any],
    levels: tuple[float, float] | None,
    ident: str,
    label: str,
) -> CheckResult:
    if counter is None:
        return
    rate = get_rate(
        value_store,
        "pfsense_counter-%s" % ident,
        timestamp,
        counter,
        raise_overflow=True,
    )
    averaged_rate = get_average(
        value_store,
        "pfsense_counter-%srate" % ident,
        timestamp,
        rate,
        backlog_minutes,
    )
    yield Metric("fw_packets_" + ident, rate, levels=levels)
    yield from check_levels_v1(
        averaged_rate,
        metric_name=f"fw_avg_packets_{ident}",
        levels_upper=levels,
        render_func=lambda x: f"{x:.2f} pkts",
        label=label,
    )


snmp_section_pfsense_counter = SimpleSNMPSection(
    name="pfsense_counter",
    detect=contains(".1.3.6.1.2.1.1.1.0", "pfsense"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12325.1.200.1",
        oids=[OIDEnd(), "2"],
    ),
    parse_function=parse_pfsense_counter,
)

check_plugin_pfsense_counter = CheckPlugin(
    name="pfsense_counter",
    service_name="pfSense Firewall Packet Rates",
    discovery_function=discovery_pfsense_counter,
    check_function=check_pfsense_counter,
    check_ruleset_name="pfsense_counter",
    check_default_parameters=CheckParameters(
        average=3,
        badoffset=(100.0, 10000.0),
        fragment=(100.0, 10000.0),
        short=(100.0, 10000.0),
        normalized=(100.0, 10000.0),
        memdrop=(100.0, 10000.0),
    ),
)
