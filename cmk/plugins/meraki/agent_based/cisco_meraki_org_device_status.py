#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    InventoryPlugin,
    InventoryResult,
    Result,
    Service,
    State,
    StringTable,
    TableRow,
)
from cmk.plugins.lib.cisco_meraki import check_last_reported_ts, load_json, MerakiAPIData


class RawPowerOverEthernet(TypedDict):
    maximum: str
    unit: str


@dataclass(frozen=True)
class PowerOverEthernet:
    maximum: str
    unit: str

    @classmethod
    def parse(cls, row: RawPowerOverEthernet) -> "PowerOverEthernet":
        return cls(row["maximum"], row["unit"])


@dataclass(frozen=True)
class PowerSupply:
    model: str
    serial: str
    status: str
    power_over_ethernet: PowerOverEthernet | None


@dataclass(frozen=True)
class DeviceStatus:
    status: str
    last_reported: datetime | None = None
    power_supplies: Mapping[str, PowerSupply] = field(default_factory=dict)

    @classmethod
    def parse(cls, row: MerakiAPIData) -> "DeviceStatus":
        raw_power_supplies = (
            raw_components.get("powerSupplies", [])
            if isinstance(raw_components := row.get("components"), dict)
            else []
        )
        return cls(
            status=str(row["status"]),
            last_reported=cls._parse_last_reported(str(row["lastReportedAt"])),
            power_supplies={
                str(raw_power_supply["slot"]): PowerSupply(
                    raw_power_supply["model"],
                    raw_power_supply["serial"],
                    raw_power_supply["status"],
                    (
                        PowerOverEthernet.parse(raw_power_over_ethernet)
                        if (raw_power_over_ethernet := raw_power_supply.get("poe"))
                        else None
                    ),
                )
                for raw_power_supply in raw_power_supplies
            },
        )

    @staticmethod
    def _parse_last_reported(raw_last_reported: str) -> datetime | None:
        try:
            return datetime.strptime(raw_last_reported, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            return None


def parse_device_status(string_table: StringTable) -> DeviceStatus | None:
    return DeviceStatus.parse(loaded_json[0]) if (loaded_json := load_json(string_table)) else None


agent_section_cisco_meraki_org_device_status = AgentSection(
    name="cisco_meraki_org_device_status",
    parse_function=parse_device_status,
)


def discover_device_status(section: DeviceStatus) -> DiscoveryResult:
    yield Service()


_STATUS_MAP = {
    "online": State.OK.value,
    "alerting": State.CRIT.value,
    "offline": State.WARN.value,
    "dormant": State.WARN.value,
}


class Parameters(TypedDict, total=False):
    status_map: Mapping[str, int]
    last_reported_upper_levels: tuple[int, int]


def check_device_status(params: Parameters, section: DeviceStatus) -> CheckResult:
    if (raw_state := params.get("status_map", {}).get(section.status)) is None:
        state = State(_STATUS_MAP[section.status])
    else:
        state = State(raw_state)
    yield Result(state=state, summary=f"Status: {section.status}")

    if section.last_reported is not None:
        if levels_upper := params.get("last_reported_upper_levels"):
            warn, crit = levels_upper
            levels_upper = (warn * 3600, crit * 3600)  # change from hours to seconds

        yield from check_last_reported_ts(
            last_reported_ts=section.last_reported.timestamp(),
            levels_upper=levels_upper,
            as_metric=True,
        )


check_plugin_cisco_meraki_org_device_status = CheckPlugin(
    name="cisco_meraki_org_device_status",
    service_name="Cisco Meraki Device Status",
    discovery_function=discover_device_status,
    check_function=check_device_status,
    check_default_parameters=Parameters(),
    check_ruleset_name="cisco_meraki_org_device_status",
)


def discover_device_status_ps(section: DeviceStatus) -> DiscoveryResult:
    for slot in section.power_supplies:
        yield Service(item=slot)


def check_device_status_ps(
    item: str, params: Mapping[str, int], section: DeviceStatus
) -> CheckResult:
    if (power_supply := section.power_supplies.get(item)) is None:
        return

    if power_supply.status.lower() == "powering":
        state = State.OK
    else:
        state = State(params.get("state_not_powering", State.WARN.value))
    yield Result(state=state, summary=f"Status: {power_supply.status}")

    if power_supply.power_over_ethernet:
        yield Result(
            state=State.OK,
            notice=(
                f"PoE: {power_supply.power_over_ethernet.maximum}"
                f" {power_supply.power_over_ethernet.unit} maximum"
            ),
        )


check_plugin_cisco_meraki_org_device_status_ps = CheckPlugin(
    name="cisco_meraki_org_device_status_ps",
    service_name="Cisco Meraki Power Supply Slot %s",
    sections=["cisco_meraki_org_device_status"],
    discovery_function=discover_device_status_ps,
    check_function=check_device_status_ps,
    check_default_parameters={},
    check_ruleset_name="cisco_meraki_org_device_status_ps",
)


def inventory_power_supplies(section: DeviceStatus) -> InventoryResult:
    for slot, power_supply in section.power_supplies.items():
        yield TableRow(
            path=["hardware", "components", "psus"],
            key_columns={
                "serial": power_supply.serial,
            },
            inventory_columns={
                "model": power_supply.model,
                "location": f"Slot {slot}",
                "manufacturer": "Cisco Meraki",
            },
        )


inventory_plugin_cisco_meraki_power_supplies = InventoryPlugin(
    name="cisco_meraki_power_supplies",
    inventory_function=inventory_power_supplies,
    sections=["cisco_meraki_org_device_status"],
)
