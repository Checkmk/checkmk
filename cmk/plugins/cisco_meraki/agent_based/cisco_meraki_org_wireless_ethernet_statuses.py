#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

# TODO: create ruleset cisco_meraki_wireless_ethernet_statuses

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import NotRequired, Self, TypedDict

from pydantic import BaseModel, Field

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    InventoryPlugin,
    InventoryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
    TableRow,
)

_SPEED_TO_BITS_PER_SEC = 12_500

type Section = Mapping[str, WirelessEthernetPort]


class PoeOrAC(BaseModel, frozen=True):
    is_connected: bool = Field(alias="isConnected")


class Power(BaseModel, frozen=True):
    mode: str
    ac: PoeOrAC
    poe: PoeOrAC


class Poe(BaseModel, frozen=True):
    standard: str


class LinkNegotiation(BaseModel, frozen=True):
    duplex: str
    raw_speed: int | None = Field(alias="speed")

    @property
    def speed(self) -> int | None:
        return self.raw_speed * _SPEED_TO_BITS_PER_SEC if self.raw_speed else None


class Port(BaseModel, frozen=True):
    name: str
    poe: Poe
    link_negotiation: LinkNegotiation = Field(alias="linkNegotiation")


class WirelessEthernetStatus(BaseModel, frozen=True):
    ports: list[Port]
    power: Power


@dataclass(frozen=True)
class WirelessEthernetPort(BaseModel, frozen=True):
    index: str
    name: str
    poe: str
    duplex: str
    speed: int | None
    power: Power

    @classmethod
    def build(cls, port: Port, power: Power) -> Self:
        return cls(
            index=port.name.split()[-1],  # "Port 2" -> "2"
            name=port.name,
            poe=port.poe.standard,
            duplex=port.link_negotiation.duplex,
            speed=port.link_negotiation.speed,
            power=power,
        )


def parse_wireless_ethernet_statuses(string_table: StringTable) -> Section:
    match string_table:
        case [[payload]] if payload:
            wireless_status = WirelessEthernetStatus.model_validate(json.loads(payload)[0])
            return {
                port.name: WirelessEthernetPort.build(port=port, power=wireless_status.power)
                for port in wireless_status.ports
            }
        case _:
            return {}


agent_section_cisco_meraki_org_wireless_ethernet_statuses = AgentSection(
    name="cisco_meraki_org_wireless_ethernet_statuses",
    parse_function=parse_wireless_ethernet_statuses,
)


class DiscoveryParams(TypedDict):
    speed: int | None


def discover_wireless_ethernet_statuses(section: Section) -> DiscoveryResult:
    for name, port in section.items():
        yield Service(item=name, parameters=DiscoveryParams(speed=port.speed))


def render_speed(speed: int | None) -> str:
    return render.nicspeed(speed) if speed is not None else "unknown"


class CheckParams(TypedDict):
    state_no_speed: int
    state_not_full_duplex: int
    state_not_on_fill_power: int
    state_speed_change: int

    # Information persisted during service discovery.
    speed: NotRequired[int]


def check_wireless_ethernet_statuses(
    item: str, params: CheckParams, section: Section
) -> CheckResult:
    if (port := section.get(item)) is None:
        return None

    prior_speed = params.get("speed")

    match port.speed:
        case int(speed) if speed != prior_speed:
            change_notice = f"Speed changed: {render_speed(prior_speed)} -> {render_speed(speed)}"
            yield Result(state=State(params["state_speed_change"]), notice=change_notice)
            yield Result(state=State.OK, summary=f"Speed: {render_speed(speed)}")
        case int(speed):
            yield Result(state=State.OK, summary=f"Speed: {render_speed(speed)}")
        case _:
            yield Result(state=State(params["state_no_speed"]), summary="Speed: unknown")

    duplex_state = 0 if port.duplex == "full" else params["state_not_full_duplex"]
    yield Result(state=State(duplex_state), summary=f"Duplex: {port.duplex}")

    power_mode_state = 0 if port.power.mode == "full" else params["state_not_on_fill_power"]
    yield Result(state=State(power_mode_state), notice=f"Power mode: {port.power.mode}")

    power_ac_summary = "AC: connected" if port.power.ac.is_connected else "AC: not connected"
    yield Result(state=State.OK, notice=power_ac_summary)

    power_poe_summary = "PoE: connected" if port.power.poe.is_connected else "PoE: not connected"
    yield Result(state=State.OK, notice=power_poe_summary)

    yield Result(state=State.OK, notice=f"PoE standard: {port.poe}")


check_plugin_cisco_meraki_org_wireless_ethernet_statuses = CheckPlugin(
    name="cisco_meraki_org_wireless_ethernet_statuses",
    service_name="Interface %s",
    discovery_function=discover_wireless_ethernet_statuses,
    check_function=check_wireless_ethernet_statuses,
    check_default_parameters=CheckParams(
        state_no_speed=State.WARN.value,
        state_not_full_duplex=State.WARN.value,
        state_not_on_fill_power=State.WARN.value,
        state_speed_change=State.WARN.value,
    ),
)


def inventory_meraki_wireless_ethernet(section: Section) -> InventoryResult:
    for port in section.values():
        yield TableRow(
            path=["networking", "interfaces"],
            key_columns={"index": port.index},
            inventory_columns={
                "name": port.name,
                "admin_status": 1,
                "oper_status": 1,
                **({"speed": render.nicspeed(port.speed)} if port.speed is not None else {}),
                "port_type": 6,
            },
        )


inventory_plugin_inv_meraki_wireless_ethernet = InventoryPlugin(
    name="inv_meraki_wireless_ethernet",
    sections=["cisco_meraki_org_wireless_ethernet_statuses"],
    inventory_function=inventory_meraki_wireless_ethernet,
)
