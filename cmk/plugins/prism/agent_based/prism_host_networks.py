#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from typing import Any, NamedTuple

import pydantic

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    RuleSetType,
    StringTable,
)
from cmk.plugins.lib import interfaces


class Stats(pydantic.BaseModel):
    in_octets: float = pydantic.Field(validation_alias="network.received_bytes")
    in_ucast: float = pydantic.Field(validation_alias="network.received_pkts")
    in_mcast: float = pydantic.Field(validation_alias="network.multicast_received_pkts")
    in_bcast: float = pydantic.Field(validation_alias="network.broadcast_received_pkts")
    in_disc: float = pydantic.Field(validation_alias="network.dropped_received_pkts")
    in_err: float = pydantic.Field(validation_alias="network.error_received_pkts")
    out_octets: float = pydantic.Field(validation_alias="network.transmitted_bytes")
    out_ucast: float = pydantic.Field(validation_alias="network.transmitted_pkts")
    out_mcast: float = pydantic.Field(validation_alias="network.multicast_transmitted_pkts")
    out_bcast: float = pydantic.Field(validation_alias="network.broadcast_transmitted_pkts")
    out_disc: float = pydantic.Field(validation_alias="network.dropped_transmitted_pkts")
    out_err: float = pydantic.Field(validation_alias="network.error_transmitted_pkts")


class RawData(pydantic.BaseModel):
    link_speed_in_kbps: None | int = None
    mac_address: None | str = None
    name: None | str = None
    stats: Stats


class InterfaceElement(NamedTuple):
    name: str
    data: RawData


def parse_prism_host_networks(
    string_table: StringTable,
) -> interfaces.Section[interfaces.InterfaceWithRates]:
    try:
        data = pydantic.TypeAdapter(list[RawData]).validate_json(string_table[0][0])
    except (IndexError, json.decoder.JSONDecodeError, pydantic.ValidationError):
        return []

    def generator() -> Iterable[InterfaceElement]:
        for element in data:
            name = element.name
            if not name:
                if element.mac_address:
                    # try to provide stable sorting without name
                    name = f"unknown_{element.mac_address}"
                else:
                    name = "unknown"
            yield InterfaceElement(name, element)

    return [
        interfaces.InterfaceWithRates(
            attributes=interfaces.Attributes(
                index=str(index),
                descr=name,
                alias=name,
                type="6",
                speed=(
                    0 if not raw_data.link_speed_in_kbps else raw_data.link_speed_in_kbps * 1000
                ),
                oper_status=("1" if raw_data.link_speed_in_kbps else "2"),
                phys_address=interfaces.mac_address_from_hexstring(raw_data.mac_address or ""),
            ),
            rates=interfaces.Rates(
                # assuming a 30 seconds window in which those counters are accumulated.
                # could be verified via /get/hosts/{uuid}/host_nics/{pnic_id}/stats
                # https://www.nutanix.dev/api_references/prism-v2-0/#/3a7cca6f493d6-list-host-host-nic-stats
                in_octets=raw_data.stats.in_octets / 30,
                in_ucast=raw_data.stats.in_ucast / 30,
                in_mcast=raw_data.stats.in_mcast / 30,
                in_bcast=raw_data.stats.in_bcast / 30,
                in_disc=raw_data.stats.in_disc / 30,
                in_err=raw_data.stats.in_err / 30,
                out_octets=raw_data.stats.out_octets / 30,
                out_ucast=raw_data.stats.out_ucast / 30,
                out_mcast=raw_data.stats.out_mcast / 30,
                out_bcast=raw_data.stats.out_bcast / 30,
                out_disc=raw_data.stats.out_disc / 30,
                out_err=raw_data.stats.out_err / 30,
            ),
            get_rate_errors=[],
        )
        for index, (name, raw_data) in enumerate(sorted(generator()))
    ]


agent_section_prism_host_networks = AgentSection(
    name="prism_host_networks",
    parse_function=parse_prism_host_networks,
)


def discovery_prism_host_networks(
    params: Sequence[Mapping[str, Any]], section: interfaces.Section[interfaces.InterfaceWithRates]
) -> DiscoveryResult:
    yield from interfaces.discover_interfaces(params, section)


def _check_prism_host_network(
    item: str,
    params: Mapping[str, Any],
    section: interfaces.Section[interfaces.InterfaceWithRates],
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    yield from interfaces.check_multiple_interfaces(item, params, section, value_store=value_store)


def check_prism_host_networks(
    item: str, params: Mapping[str, Any], section: interfaces.Section[interfaces.InterfaceWithRates]
) -> CheckResult:
    yield from _check_prism_host_network(item, params, section, get_value_store())


check_plugin_prism_host_networks = CheckPlugin(
    name="prism_host_networks",
    service_name="NTNX NIC %s",
    sections=["prism_host_networks"],
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    discovery_function=discovery_prism_host_networks,
    check_function=check_prism_host_networks,
    check_ruleset_name="interfaces",
)
