#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

# Pydantic requires the property to be under computed_field to work.
# mypy: disable-error-code="prop-decorator"

import json
from datetime import datetime
from typing import TypedDict

from pydantic import BaseModel, computed_field, Field

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.cisco_meraki.lib.constants import DEFAULT_TIMESPAN
from cmk.plugins.cisco_meraki.lib.schema import UplinkUsageByInterface
from cmk.plugins.cisco_meraki.lib.type_defs import PossiblyMissing

type Section = ApplianceStatus


class Uplink(BaseModel, frozen=True):
    gateway: str | None
    interface: str
    ip: str | None
    ip_assigned_by: str | None = Field(alias="ipAssignedBy")
    primary_dns: str | None = Field(alias="primaryDns")
    public_ip: str | None = Field(alias="publicIp")
    secondary_dns: str | None = Field(alias="secondaryDns")
    status: str


class HighAvailability(BaseModel, frozen=True):
    enabled: bool
    role: str


class ApplianceStatus(BaseModel, frozen=True):
    high_availability: HighAvailability = Field(alias="highAvailability")
    last_reported_at: datetime = Field(alias="lastReportedAt")
    model: str
    network_name: str = Field(alias="networkName")
    serial: str
    uplinks_list: list[Uplink] = Field(alias="uplinks")
    usage_by_interface: PossiblyMissing[UplinkUsageByInterface] = Field(
        None, alias="usageByInterface"
    )

    @computed_field
    @property
    def uplinks(self) -> dict[str, Uplink]:
        return {up.interface: up for up in self.uplinks_list}


def parse_appliance_uplinks(string_table: StringTable) -> Section | None:
    match string_table:
        case [[payload]] if payload:
            return ApplianceStatus.model_validate(json.loads(payload)[0])
        case _:
            return None


agent_section_cisco_meraki_org_appliance_uplinks = AgentSection(
    name="cisco_meraki_org_appliance_uplinks",
    parse_function=parse_appliance_uplinks,
)


def discover_appliance_uplinks(section: Section) -> DiscoveryResult:
    for uplink in section.uplinks:
        yield Service(item=uplink)


def _get_bits_by_timespan(value: int) -> float:
    return value * 8 / DEFAULT_TIMESPAN


def _render_network_bandwidth_bits_to_bytes(value: float) -> str:
    return render.networkbandwidth(value / 8)


class CheckParams(TypedDict):
    show_traffic: bool
    status_map: dict[str, int]


def check_appliance_uplinks(item: str, params: CheckParams, section: Section) -> CheckResult:
    if (uplink := section.uplinks.get(item)) is None:
        return None

    # TODO: cannot use 'not connected' in params anymore - still relevant? (note from MKP)
    status_map = params["status_map"]
    status_map["not connected"] = 1

    yield Result(
        state=State(status_map.get(uplink.status, 3)),
        summary=f"Status: {uplink.status}",
    )

    if uplink.ip:
        yield Result(state=State.OK, summary=f"IP: {uplink.ip}")
    if uplink.public_ip:
        yield Result(state=State.OK, summary=f"Public IP: {uplink.public_ip}")

    yield Result(state=State.OK, notice=f"Network: {section.network_name}")

    if (
        params["show_traffic"]
        and uplink.status == "active"
        and section.usage_by_interface
        and (usage := section.usage_by_interface.get(uplink.interface))
    ):
        if (received := usage.get("received")) is not None:
            yield from check_levels(
                value=_get_bits_by_timespan(received),
                label="In",
                metric_name="if_in_bps",
                render_func=_render_network_bandwidth_bits_to_bytes,
            )
        if (sent := usage.get("sent")) is not None:
            yield from check_levels(
                value=_get_bits_by_timespan(sent),
                label="Out",
                metric_name="if_out_bps",
                render_func=_render_network_bandwidth_bits_to_bytes,
            )

    # TODO: is this useful? System with H/A enabled=True is required. (note from MKP)
    yield Result(state=State.OK, notice=f"H/A enabled: {section.high_availability.enabled}")
    yield Result(state=State.OK, notice=f"H/A role: {section.high_availability.role}")

    if uplink.gateway:
        yield Result(state=State.OK, notice=f"Gateway: {uplink.gateway}")
    if uplink.ip_assigned_by:
        yield Result(state=State.OK, notice=f"IP assigned by: {uplink.ip_assigned_by}")
    if uplink.primary_dns:
        yield Result(state=State.OK, notice=f"Primary DNS: {uplink.primary_dns}")
    if uplink.secondary_dns:
        yield Result(state=State.OK, notice=f"Secondary DNS: {uplink.secondary_dns}")


check_plugin_cisco_meraki_org_appliance_uplinks = CheckPlugin(
    name="cisco_meraki_org_appliance_uplinks",
    service_name="Uplink %s",
    discovery_function=discover_appliance_uplinks,
    check_function=check_appliance_uplinks,
    check_ruleset_name="cisco_meraki_org_appliance_uplinks",
    check_default_parameters=CheckParams(
        status_map={
            "active": State.OK.value,
            "ready": State.OK.value,
            "connecting": State.WARN.value,
            "not_connected": State.WARN.value,
            "failed": State.CRIT.value,
        },
        show_traffic=True,
    ),
)
