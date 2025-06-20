#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import time
from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    RuleSetType,
    SimpleSNMPSection,
    SNMPSection,
    SNMPTree,
    State,
    StringByteTable,
    StringTable,
)
from cmk.plugins.lib import if64, interfaces, uptime

If64AdmSection = Mapping[str, str]


def parse_if64adm(string_table: StringTable) -> If64AdmSection:
    return {
        index: admin_status
        for (index, admin_status) in string_table
        if interfaces.saveint(index) > 0 and admin_status
    }


@dataclasses.dataclass(frozen=True)
class If64WithUptime:
    uptime: uptime.Section | None
    interfaces: interfaces.Section[interfaces.InterfaceWithCounters]


def parse_if64_with_uptime(string_table: Sequence[StringByteTable]) -> If64WithUptime:
    raw_uptime, raw_if64 = string_table
    return If64WithUptime(
        uptime=uptime.parse_snmp_uptime([[str(w) for w in l] for l in raw_uptime]),
        interfaces=if64.parse_if64(raw_if64),
    )


snmp_section_if64 = SNMPSection(
    name="if64",
    parse_function=parse_if64_with_uptime,
    fetch=[
        uptime.UPTIME_TREE,
        SNMPTree(
            base=if64.BASE_OID,
            oids=if64.END_OIDS,
        ),
    ],
    detect=if64.HAS_ifHCInOctets,
    supersedes=["if", "statgrab_net", "if32_with_alias"],
)

# Note: This section is by default deactivated
# (hard-coded in the defaul config `disabled_snmp_sections`)
# to reduce SNMP traffic.
# To activate it, use the ruleset `snmp_exclude_sections`.
snmp_section_if64adm = SimpleSNMPSection(
    name="if64adm",
    parse_function=parse_if64adm,
    fetch=SNMPTree(
        # If we simply used if64.BASE_OID here, the backend would complain that the base OID could
        # be extended
        base=f"{if64.BASE_OID}.2.2.1",
        oids=[
            "1",  # ifIndex
            "7",  # ifAdminStatus
        ],
    ),
    detect=if64.HAS_ifHCInOctets,
)


def _add_admin_status_to_ifaces(
    section_if64: interfaces.Section[interfaces.TInterfaceType],
    section_if64adm: If64AdmSection | None,
) -> None:
    if section_if64adm is None:
        return
    for iface in section_if64:
        if (admin_status := section_if64adm.get(iface.attributes.index)) is not None:
            iface.attributes.admin_status = admin_status


def _uptime_or_server_time(now: float, section_uptime: uptime.Section | None) -> float:
    if section_uptime is None:
        return now
    return section_uptime.uptime_sec or now


def discover_if64(
    params: Sequence[Mapping[str, Any]],
    section_if64: If64WithUptime | None,
    section_if64adm: If64AdmSection | None,
) -> DiscoveryResult:
    if section_if64 is None:
        return
    _add_admin_status_to_ifaces(section_if64.interfaces, section_if64adm)
    yield from interfaces.discover_interfaces(
        params,
        section_if64.interfaces,
    )


def _check_timestamp(timestamp: float, value_store: MutableMapping[str, Any]) -> CheckResult:
    previous_timestamp: float | None = value_store.get("timestamp_previous")
    value_store["timestamp_previous"] = timestamp
    if previous_timestamp is None:
        return
    if previous_timestamp == timestamp:
        yield Result(
            state=State.OK,
            notice="The uptime did not change since the last check cycle. "
            "It is likely that no new data was collected.",
        )
    elif previous_timestamp > timestamp:
        yield Result(
            state=State.OK,
            notice="The uptime has decreased since the last check cycle. "
            "The device might have rebooted or its uptime counter overflowed.",
        )


def check_if64(
    item: str,
    params: Mapping[str, Any],
    section_if64: If64WithUptime | None,
    section_if64adm: If64AdmSection | None,
) -> CheckResult:
    if section_if64 is None:
        return
    _add_admin_status_to_ifaces(section_if64.interfaces, section_if64adm)
    timestamp = _uptime_or_server_time(time.time(), section_if64.uptime)
    yield from interfaces.check_multiple_interfaces(
        item,
        params,
        section_if64.interfaces,
        timestamps=[timestamp] * len(section_if64.interfaces),
    )
    yield from _check_timestamp(timestamp, get_value_store())


def _check_timestamps(
    timestamps: Mapping[str, float], value_store: MutableMapping[str, Any]
) -> CheckResult:
    previous_timestamps: Mapping[str, float] = value_store.get("timestamps_previous", {})
    value_store["timestamps_previous"] = timestamps
    nodes_without_uptime_increase = [
        node
        for node, timestamp in timestamps.items()
        if (previous_timestamp := previous_timestamps.get(node)) is not None
        and previous_timestamp == timestamp
    ]
    if nodes_without_uptime_increase:
        yield Result(
            state=State.OK,
            notice="The uptime did not change since the last check cycle for these node(s): "
            + ", ".join(nodes_without_uptime_increase)
            + "\n"
            "It is likely that no new data was collected.",
        )
    nodes_with_uptime_decrease = [
        node
        for node, timestamp in timestamps.items()
        if (previous_timestamp := previous_timestamps.get(node)) is not None
        and previous_timestamp > timestamp
    ]
    if nodes_with_uptime_decrease:
        yield Result(
            state=State.OK,
            notice="The uptime has decreased since the last check cycle for these node(s): "
            + ", ".join(nodes_without_uptime_increase)
            + "\n"
            "The device might have rebooted or its uptime counter overflowed.",
        )


def cluster_check_if64(
    item: str,
    params: Mapping[str, Any],
    section_if64: Mapping[str, If64WithUptime | None],
    section_if64adm: Mapping[str, If64AdmSection | None],
) -> CheckResult:
    sections_w_admin_status: dict[str, interfaces.Section[interfaces.InterfaceWithCounters]] = {}
    for node_name, node_section_if64 in section_if64.items():
        if node_section_if64 is not None:
            _add_admin_status_to_ifaces(node_section_if64.interfaces, section_if64adm[node_name])
            sections_w_admin_status[node_name] = node_section_if64.interfaces

    ifaces = []
    timestamp_per_iface = []
    node_to_timestamp = {}
    now = time.time()
    for node, node_ifaces in sections_w_admin_status.items():
        timestamp = _uptime_or_server_time(
            now,
            None if (s := section_if64[node]) is None else s.uptime,
        )
        node_to_timestamp[node] = timestamp
        for iface in node_ifaces or ():
            ifaces.append(
                dataclasses.replace(
                    iface,
                    attributes=dataclasses.replace(
                        iface.attributes,
                        node=node,
                    ),
                )
            )
            timestamp_per_iface.append(timestamp)
    yield from interfaces.check_multiple_interfaces(
        item,
        params,
        ifaces,
        timestamps=timestamp_per_iface,
    )
    yield from _check_timestamps(node_to_timestamp, get_value_store())


check_plugin_if64 = CheckPlugin(
    name="if64",
    sections=["if64", "if64adm"],
    service_name="Interface %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=discover_if64,
    check_ruleset_name="interfaces",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=check_if64,
    cluster_check_function=cluster_check_if64,
)
