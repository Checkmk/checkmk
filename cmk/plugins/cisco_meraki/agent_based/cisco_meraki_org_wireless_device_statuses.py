#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

# Pydantic requires the property to be under computed_field to work.
# mypy: disable-error-code="prop-decorator"

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypedDict

from pydantic import BaseModel, computed_field, Field

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)

_MHZ_TO_HZ = 1_000_000

type Section = WirelessDeviceStatusInfo


class BasicServiceSet(BaseModel, frozen=True):
    ssid_name: str = Field(alias="ssidName")
    ssid_number: int = Field(alias="ssidNumber")
    enabled: bool
    band: str
    channel: int
    channel_width: str | None = Field(alias="channelWidth")
    power: str | None
    visible: bool
    broadcasting: bool

    @computed_field
    @property
    def normalized_channel_width(self) -> int | None:
        if self.channel_width is None:
            return None

        value, *_ = self.channel_width.split()
        return int(value) * _MHZ_TO_HZ

    @computed_field
    @property
    def normalized_power(self) -> int | None:
        if self.power is None:
            return None

        value, *_ = self.power.split()
        return int(value)


class WirelessDeviceStatus(BaseModel, frozen=True):
    ssids: list[BasicServiceSet] = Field(alias="basicServiceSets")


@dataclass(frozen=True)
class WirelessDeviceStatusInfo:
    ssids: Mapping[str, BasicServiceSet]
    bands: Mapping[str, BasicServiceSet]


def parse_wireless_device_statuses(string_table: StringTable) -> Section | None:
    match string_table:
        case [[payload]] if payload:
            status = WirelessDeviceStatus.model_validate(json.loads(payload)[0])
            return WirelessDeviceStatusInfo(
                ssids={ssid.ssid_name: ssid for ssid in status.ssids},
                bands={ssid.band: ssid for ssid in status.ssids},
            )
        case _:
            return None


agent_section_cisco_meraki_org_wireless_device_statuses = AgentSection(
    name="cisco_meraki_org_wireless_device_statuses",
    parse_function=parse_wireless_device_statuses,
)


def discover_wireless_device_statuses_ssids(section: Section) -> DiscoveryResult:
    for ssid_name in section.ssids:
        yield Service(item=ssid_name)


class CheckParams(TypedDict):
    state_if_not_enabled: int


def check_wireless_device_statuses_ssids(
    item: str, params: CheckParams, section: Section
) -> CheckResult:
    if (ssid := section.ssids.get(item)) is None:
        return

    if not ssid.enabled:
        yield Result(state=State(params["state_if_not_enabled"]), summary="Status: Disabled")
        return

    yield Result(state=State.OK, summary="Status: Enabled")
    yield Result(state=State.OK, notice=f"Visible: {ssid.visible}")
    yield Result(state=State.OK, notice=f"SSID number: {ssid.ssid_number}")


check_plugin_cisco_meraki_org_wireless_device_statuses_ssids = CheckPlugin(
    name="cisco_meraki_org_wireless_device_statuses_ssids",
    sections=["cisco_meraki_org_wireless_device_statuses"],
    check_ruleset_name="cisco_meraki_org_wireless_device_statuses_ssids",
    service_name="SSID %s",
    discovery_function=discover_wireless_device_statuses_ssids,
    check_function=check_wireless_device_statuses_ssids,
    check_default_parameters=CheckParams(
        state_if_not_enabled=State.WARN.value,
    ),
)


def discover_wireless_device_statuses_bands(section: Section) -> DiscoveryResult:
    for band in section.bands:
        yield Service(item=band)


def check_wireless_device_statuses_bands(item: str, section: Section) -> CheckResult:
    if (ssid := section.bands.get(item)) is None:
        return

    yield Result(state=State.OK, summary=f"Channel: {ssid.channel}")
    yield Result(state=State.OK, summary=f"Channel width: {ssid.channel_width}")
    yield Result(state=State.OK, summary=f"Power: {ssid.power}")
    yield Result(state=State.OK, notice=f"Broadcasting: {ssid.broadcasting}")

    yield Metric(name="channel", value=ssid.channel)

    if ssid.normalized_channel_width:
        yield Metric(name="channel_width", value=ssid.normalized_channel_width)

    if ssid.normalized_power:
        yield Metric(name="signal_power", value=ssid.normalized_power)


check_plugin_cisco_meraki_org_wireless_device_statuses_bands = CheckPlugin(
    name="cisco_meraki_org_wireless_device_statuses_bands",
    sections=["cisco_meraki_org_wireless_device_statuses"],
    service_name="Radio %s",
    discovery_function=discover_wireless_device_statuses_bands,
    check_function=check_wireless_device_statuses_bands,
    check_default_parameters=None,
)
