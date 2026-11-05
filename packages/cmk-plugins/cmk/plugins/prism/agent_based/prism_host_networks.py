#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import json
import time
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
from cmk.plugins.prism.v4_models import HostNics


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


class _Nic(NamedTuple):
    name: str
    mac_address: str | None
    link_speed_in_kbps: int | None
    is_up: bool
    rates: interfaces.Rates


def _name(name: str | None, mac_address: str | None) -> str:
    if name:
        return name
    # try to provide stable sorting without name
    return f"unknown_{mac_address}" if mac_address else "unknown"


def _section(
    nics: Iterable[_Nic], timestamp: float
) -> interfaces.Section[interfaces.InterfaceWithRates]:
    return [
        interfaces.InterfaceWithRates(
            attributes=interfaces.Attributes(
                index=str(index),
                descr=nic.name,
                alias=nic.name,
                type="6",
                speed=0 if not nic.link_speed_in_kbps else nic.link_speed_in_kbps * 1000,
                oper_status="1" if nic.is_up else "2",
                phys_address=interfaces.mac_address_from_hexstring(nic.mac_address or ""),
            ),
            rates=nic.rates,
            get_rate_errors=[],
            timestamp=timestamp,
        )
        for index, nic in enumerate(sorted(nics, key=lambda nic: nic.name))
    ]


def parse_prism_host_networks_pure(
    string_table: StringTable,
    timestamp: float,
) -> interfaces.Section[interfaces.InterfaceWithRates]:
    try:
        data = pydantic.TypeAdapter(list[RawData]).validate_json(string_table[0][0])
    except IndexError, json.decoder.JSONDecodeError, pydantic.ValidationError:
        return []

    return _section(
        (
            _Nic(
                name=_name(raw_data.name, raw_data.mac_address),
                mac_address=raw_data.mac_address,
                link_speed_in_kbps=raw_data.link_speed_in_kbps,
                is_up=bool(raw_data.link_speed_in_kbps),
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
            )
            for raw_data in data
        ),
        timestamp,
    )


def parse_prism_host_networks(
    string_table: StringTable,
) -> interfaces.Section[interfaces.InterfaceWithRates]:
    return parse_prism_host_networks_pure(string_table, time.time())


agent_section_prism_host_networks = AgentSection(
    name="prism_host_networks",
    parse_function=parse_prism_host_networks,
)


def parse_prism_host_networks_v2(
    string_table: StringTable,
) -> interfaces.Section[interfaces.InterfaceWithRates]:
    """The v4 API has no traffic counters, so the interfaces come without rates"""
    if not string_table:
        return []
    return _section(
        (
            _Nic(
                name=_name(nic.name, nic.mac_address),
                mac_address=nic.mac_address,
                link_speed_in_kbps=nic.link_speed_in_kbps,
                is_up=bool(nic.link_speed_in_kbps)
                if nic.interface_status is None
                else nic.interface_status == "1",
                rates=interfaces.Rates(),
            )
            for nic in HostNics.model_validate_json(string_table[0][0]).root
        ),
        time.time(),
    )


agent_section_prism_host_networks_v2 = AgentSection(
    name="prism_host_networks_v2",
    parsed_section_name="prism_host_networks",
    parse_function=parse_prism_host_networks_v2,
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
