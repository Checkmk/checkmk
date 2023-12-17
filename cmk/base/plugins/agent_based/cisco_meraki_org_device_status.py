#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# enhancements by thl-cmk[at]outlook[dot]com, https://thl-cmk.hopto.org
# - made device status configurable via WATO
# - added last_reported as check_levels, levels_upper can be configured via WATO
# - added power supplies
# - added unknown components (for discovery) -> removed
# - removed device offline check from device status discovery function
# - added power supplies to inventory (hardware -> physical components -> power supplies)
# - changed item from "Cisco Meraki Device" Status to "Device Status" -> we know this is a Meraki device ;-)
#
# 2023-11-09: fixed crash if no powersupply in components
# 2023-11-19: fixed crash in inventory if no powersupply in components
# 2023-12-17: refactored to use pydantic

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any, Union

from pydantic import BaseModel, BeforeValidator, Field

from cmk.plugins.lib.cisco_meraki import check_last_reported_ts, load_json, MerakiAPIData

from .agent_based_api.v1 import register, Result, Service, State, TableRow
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, InventoryResult, StringTable

# sample device status
__device_status = [
    {
        "components": {
            "powerSupplies": [
                {
                    "model": "PWR-MS320-250WAC",
                    "poe": {"maximum": 0, "unit": "watts"},
                    "serial": "Q0YY-Y0Y0-YYYY",
                    "slot": 1,
                    "status": "powering",
                },
                {
                    "model": "PWR-MS320-250WAC",
                    "poe": {"maximum": 0, "unit": "watts"},
                    "serial": "Q1ZZ-Z1ZZ-ZZZZ",
                    "slot": 2,
                    "status": "powering",
                },
            ]
        },
        "gateway": "10.10.10.254",
        "ipType": "static",
        "lanIp": "10.10.10.250",
        "lastReportedAt": "2023-12-17T09:35:08.496000Z",
        "mac": "aa:aa:aa:aa:aa:aa",
        "model": "MS410-16",
        "name": "SW01",
        "networkId": "L_012345678901234567",
        "primaryDns": "8.8.8.8",
        "productType": "switch",
        "publicIp": "99.99.99.99",
        "secondaryDns": "1.1.1.1",
        "serial": "Q3XX-X3XX-XXX3",
        "status": "online",
        "tags": [],
    }
]


class Poe(BaseModel):
    maximum: int = Field(alias="maximum")
    unit: str = Field(alias="unit")


def _parse_str(raw_str: Any) -> str:
    return str(raw_str)


PsStr = Annotated[Union[str, None], BeforeValidator(_parse_str)]


class PowerSupply(BaseModel):
    slot: PsStr = Field(alias="slot")
    model: str = Field(alias="model")
    serial: str = Field(alias="serial")
    status: str = Field(alias="status")
    poe: Poe = Field(alias="poe")


@dataclass
class DeviceStatus:
    status: str | None = None
    last_reported: datetime | None = None
    power_supplies: Sequence[PowerSupply] | None = None

    @classmethod
    def parse(cls, row: MerakiAPIData) -> "DeviceStatus":
        new_cls = cls()
        new_cls.last_reported = cls._parse_last_reported(str(row["lastReportedAt"]))
        new_cls.status = str(row["status"])
        new_cls.power_supplies = []

        if isinstance(raw_components := row.get("components"), dict):
            for raw_power_supply in raw_components.get("powerSupplies", []):
                new_cls.power_supplies.append(PowerSupply.model_validate(raw_power_supply))

        return new_cls

    @staticmethod
    def _parse_last_reported(raw_last_reported: str) -> datetime | None:
        try:
            return datetime.strptime(raw_last_reported, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            return None


def parse_device_status(string_table: StringTable) -> DeviceStatus | None:
    return DeviceStatus.parse(loaded_json[0]) if (loaded_json := load_json(string_table)) else None


register.agent_section(
    name="cisco_meraki_org_device_status",
    parse_function=parse_device_status,
)


def discover_device_status(section: DeviceStatus | None) -> DiscoveryResult:
    if section:
        yield Service()


_STATUS_MAP = {
    "online": State.OK.value,  # changed to int to be compatible with wato
    "alerting": State.CRIT.value,
    "offline": State.WARN.value,
    "dormant": State.WARN.value,  # TODO not sure -> now configurable via WATO
}


def check_device_status(params: Mapping[str, Any], section: DeviceStatus | None) -> CheckResult:
    if not section:
        return

    _STATUS_MAP.update(params.get("status_map", {}))

    yield Result(
        state=State(_STATUS_MAP.get(str(section.status), State.CRIT.value)),
        summary=f"Status: {section.status}",
    )

    if section.last_reported is not None:
        if levels_upper := params.get("last_reported_upper_levels", None):
            warn, crit = levels_upper
            levels_upper = (warn * 3600, crit * 3600)  # change from hours to seconds

        yield from check_last_reported_ts(
            last_reported_ts=section.last_reported.timestamp(),
            levels_upper=levels_upper,
            as_metric=True,
        )


register.check_plugin(
    name="cisco_meraki_org_device_status",
    service_name="Device Status",
    discovery_function=discover_device_status,
    check_function=check_device_status,
    check_default_parameters={},
    check_ruleset_name="cisco_meraki_org_device_status",
)


def discover_device_status_ps(section: DeviceStatus | None) -> DiscoveryResult:
    if not section or not section.power_supplies:
        return

    for power_supply in section.power_supplies:
        yield Service(item=power_supply.slot)


def check_device_status_ps(
    item: str, params: Mapping[str, Any], section: DeviceStatus | None
) -> CheckResult:
    if not section or not section.power_supplies:
        return

    for power_supply in section.power_supplies:
        if power_supply.slot == item:
            if power_supply.status.lower() == "powering":
                yield Result(state=State.OK, summary=f"Status: {power_supply.status}")
            else:
                yield Result(
                    state=State(params.get("state_not_powering", State.WARN.value)),
                    summary=f"Status: {power_supply.status}",
                )

            if power_supply.model:
                yield Result(state=State.OK, notice=f"Model: {power_supply.model}")
            if power_supply.serial:
                yield Result(state=State.OK, notice=f"Serial: {power_supply.serial}")
            if power_supply.poe:
                yield Result(
                    state=State.OK,
                    notice=f"PoE: {power_supply.poe.maximum} {power_supply.poe.unit} maximum",
                )
            break


register.check_plugin(
    name="cisco_meraki_org_device_status_ps",
    service_name="Power supply slot %s",
    sections=["cisco_meraki_org_device_status"],
    discovery_function=discover_device_status_ps,
    check_function=check_device_status_ps,
    check_default_parameters={},
    check_ruleset_name="cisco_meraki_org_device_status_ps",
)


#
# inventory of power supplies overview
#
def inventory_power_supplies(section: DeviceStatus | None) -> InventoryResult:
    if not section or not section.power_supplies:
        return

    path = ["hardware", "components", "psus"]
    index = 1
    for power_supply in section.power_supplies:
        yield TableRow(
            path=path,
            key_columns={"serial": power_supply.serial},
            inventory_columns={
                "model": power_supply.model,
                "location": f"Slot {power_supply.slot}",
                "index": index,
                "manufacturer": "Cisco Meraki",
            },
        )
        index += 1


register.inventory_plugin(
    name="cisco_meraki_power_supplies",
    inventory_function=inventory_power_supplies,
    sections=["cisco_meraki_org_device_status"],
)
