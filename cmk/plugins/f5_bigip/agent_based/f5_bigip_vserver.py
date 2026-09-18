#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
import time
from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field
from typing import TypedDict

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    GetRateError,
    LevelsT,
    Metric,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.f5_bigip.lib import F5_BIGIP

_NO_LEVELS: LevelsT[float] = ("no_levels", None)

# Current server status, as reported by the device:
# 0 - NONE:   disabled
# 1 - GREEN:  available in some capacity
# 2 - YELLOW: not currently available
# 3 - RED:    not available
# 4 - BLUE:   availability is unknown
# 5 - GREY:   unlicensed
MAP_SERVER_STATUS = {
    "0": (State.WARN, "is disabled"),
    "1": (State.OK, "is up and available"),
    "2": (State.CRIT, "is currently not available"),
    "3": (State.CRIT, "is not available"),
    "4": (State.WARN, "availability is unknown"),
    "5": (State.UNKNOWN, "is unlicensed"),
}

MAP_ENABLED = {
    "0": "NONE",
    "1": "enabled",
    "2": "disabled",
    "3": "disabled by parent",
}

_CHILDREN_POOL_MEMBERS_DOWN = "the children pool member(s) are down"

# The counters that are turned into rates, and the value store keys they use.
_AGGREGATION_KEYS = (
    "if_in_pkts",
    "if_out_pkts",
    "if_in_octets",
    "if_out_octets",
    "connections_rate",
    "packet_velocity_asic",
)

# key, index in the SNMP row, factor
_COUNTERS = (
    ("connections_duration_min", 5, 0.001),
    ("connections_duration_max", 6, 0.001),
    ("connections_duration_mean", 7, 0.001),
    ("if_in_pkts", 8, 1.0),
    ("if_out_pkts", 9, 1.0),
    ("if_in_octets", 10, 1.0),
    ("if_out_octets", 11, 1.0),
    ("connections_rate", 12, 1.0),
    ("connections", 13, 1.0),
    ("packet_velocity_asic", 14, 1.0),
)


def _packets_per_second(value: float) -> str:
    return f"{value}/s"


class VServerParams(TypedDict, total=False):
    state: Mapping[str, int]
    connections: LevelsT[float]
    if_in_octets: LevelsT[float]
    if_in_octets_lower: LevelsT[float]
    if_out_octets: LevelsT[float]
    if_out_octets_lower: LevelsT[float]
    if_total_octets: LevelsT[float]
    if_total_octets_lower: LevelsT[float]
    if_in_pkts: LevelsT[float]
    if_in_pkts_lower: LevelsT[float]
    if_out_pkts: LevelsT[float]
    if_out_pkts_lower: LevelsT[float]
    if_total_pkts: LevelsT[float]
    if_total_pkts_lower: LevelsT[float]


@dataclass(frozen=True)
class VServer:
    status: str
    enabled: str
    detail: str
    ip_address: str
    counters: Mapping[str, Sequence[float]] = field(default_factory=dict)


Section = Mapping[str, VServer]


def get_ip_address_human_readable(ip_addr: str) -> str:
    r"""Render the packed address the device reports.

    >>> get_ip_address_human_readable("\xc2;xJ")
    '194.59.120.74'
    """
    try:
        ip_addr_binary = bytes(ord(x) for x in ip_addr)
    except ValueError:
        return "-"

    if len(ip_addr_binary) == 4:
        return socket.inet_ntop(socket.AF_INET, ip_addr_binary)
    if len(ip_addr_binary) == 16:
        return socket.inet_ntop(socket.AF_INET6, ip_addr_binary)
    return "-"


def parse_f5_bigip_vserver(string_table: StringTable) -> Section:
    vservers: dict[str, dict[str, list[float]]] = {}
    attributes: dict[str, tuple[str, str, str, str]] = {}

    for line in string_table:
        name = line[0]
        attributes.setdefault(
            name, (line[1], line[2], line[3], get_ip_address_human_readable(line[4]))
        )
        counters = vservers.setdefault(name, {})

        for key, index, factor in _COUNTERS:
            # The columns of OIDs the device does not answer are empty. Every other value
            # is a counter and has to be a number; one that is not means the device
            # violated the MIB, which we let crash rather than silently drop.
            if not (value := line[index]):
                continue
            counters.setdefault(key, []).append(int(value) * factor)

    return {
        name: VServer(
            status=status,
            enabled=enabled,
            detail=detail,
            ip_address=ip_address,
            counters=vservers[name],
        )
        for name, (status, enabled, detail, ip_address) in attributes.items()
    }


def discover_f5_bigip_vserver(section: Section) -> DiscoveryResult:
    yield from (Service(item=name) for name in section)


def _aggregate(
    value_store: MutableMapping[str, object],
    now: float,
    vserver: VServer,
) -> Mapping[str, float]:
    aggregation: dict[str, float] = {}

    for key in _AGGREGATION_KEYS:
        if key not in vserver.counters:
            continue
        total = 0.0
        raised = False
        for index, value in enumerate(vserver.counters[key]):
            try:
                total += get_rate(value_store, f"{key}.{index}", now, value, raise_overflow=True)
            except GetRateError:
                raised = True
        if not raised:
            aggregation[key] = total

    for key, function in (
        ("connections_duration_min", min),
        ("connections_duration_max", max),
        ("connections", sum),
    ):
        if values := vserver.counters.get(key):
            aggregation[key] = float(function(values))
    if values := vserver.counters.get("connections_duration_mean"):
        aggregation["connections_duration_mean"] = float(sum(values)) / len(values)

    for unit in ("octets", "pkts"):
        in_key, out_key = f"if_in_{unit}", f"if_out_{unit}"
        if in_key in aggregation or out_key in aggregation:
            aggregation[f"if_total_{unit}"] = aggregation.get(in_key, 0.0) + aggregation.get(
                out_key, 0.0
            )

    return aggregation


def check_f5_bigip_vserver(item: str, params: VServerParams, section: Section) -> CheckResult:
    if (vserver := section.get(item)) is None:
        return

    enabled_state = State.OK if vserver.enabled in MAP_ENABLED else State.WARN
    enabled_text = MAP_ENABLED.get(vserver.enabled, "in unknown state")
    yield Result(
        state=enabled_state,
        summary=f"Virtual Server with IP {vserver.ip_address} is {enabled_text}",
    )

    state_map = params.get("state", {})
    state, state_readable = MAP_SERVER_STATUS.get(
        vserver.status, (State.UNKNOWN, f"Unhandled status ({vserver.status})")
    )
    state = State(state_map.get(state_readable.replace(" ", "_"), state))

    # Special handling: statement from the network team. Not available is uncritical
    # when the children are down.
    if vserver.status == "3" and vserver.detail.lower() == _CHILDREN_POOL_MEMBERS_DOWN:
        state = State(state_map.get("children_pool_members_down_if_not_available", 0))

    yield Result(state=state, summary=f"State {state_readable}, Detail: {vserver.detail}")

    aggregation = _aggregate(get_value_store(), time.time(), vserver)

    if "connections" in aggregation:
        yield from check_levels(
            aggregation["connections"],
            levels_upper=params.get("connections") or _NO_LEVELS,
            render_func=lambda value: f"{value:.0f}",
            label="Client connections",
        )
        yield from (Metric(key, value) for key, value in sorted(aggregation.items()))

    if "connections_rate" in aggregation:
        yield Result(
            state=State.OK,
            summary=f"Connections rate: {aggregation['connections_rate']:.2f}/sec",
        )

    _bandwidth, _per_second = render.iobandwidth, _packets_per_second
    for value_key, levels_upper, levels_lower, label, render_func in (
        (
            "if_in_octets",
            params.get("if_in_octets"),
            params.get("if_in_octets_lower"),
            "Incoming bytes",
            _bandwidth,
        ),
        (
            "if_out_octets",
            params.get("if_out_octets"),
            params.get("if_out_octets_lower"),
            "Outgoing bytes",
            _bandwidth,
        ),
        (
            "if_total_octets",
            params.get("if_total_octets"),
            params.get("if_total_octets_lower"),
            "Total bytes",
            _bandwidth,
        ),
        (
            "if_in_pkts",
            params.get("if_in_pkts"),
            params.get("if_in_pkts_lower"),
            "Incoming packets",
            _per_second,
        ),
        (
            "if_out_pkts",
            params.get("if_out_pkts"),
            params.get("if_out_pkts_lower"),
            "Outgoing packets",
            _per_second,
        ),
        (
            "if_total_pkts",
            params.get("if_total_pkts"),
            params.get("if_total_pkts_lower"),
            "Total packets",
            _per_second,
        ),
    ):
        if value_key not in aggregation or (levels_upper is None and levels_lower is None):
            continue

        yield from check_levels(
            aggregation[value_key],
            levels_upper=levels_upper or _NO_LEVELS,
            levels_lower=levels_lower or _NO_LEVELS,
            render_func=render_func,
            label=label,
            notice_only=True,
        )


snmp_section_f5_bigip_vserver = SimpleSNMPSection(
    name="f5_bigip_vserver",
    detect=F5_BIGIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3375.2.2.10",
        oids=[
            "13.2.1.1",
            "13.2.1.2",
            "13.2.1.3",
            "13.2.1.5",
            "1.2.1.3",
            "2.3.1.2",
            "2.3.1.3",
            "2.3.1.4",
            "2.3.1.6",
            "2.3.1.8",
            "2.3.1.7",
            "2.3.1.9",
            "2.3.1.11",
            "2.3.1.12",
            "2.3.1.25",
        ],
    ),
    parse_function=parse_f5_bigip_vserver,
)


check_plugin_f5_bigip_vserver = CheckPlugin(
    name="f5_bigip_vserver",
    service_name="Virtual Server %s",
    discovery_function=discover_f5_bigip_vserver,
    check_function=check_f5_bigip_vserver,
    check_ruleset_name="f5_bigip_vserver",
    check_default_parameters=VServerParams(),
)
