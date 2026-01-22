#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Pydantic requires the property to be under computed_field to work.
# mypy: disable-error-code="prop-decorator"

import json
from collections.abc import Mapping
from datetime import datetime
from typing import TypedDict

from pydantic import BaseModel, computed_field, Field

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
from cmk.plugins.cisco_meraki.lib.type_defs import PossiblyMissing
from cmk.plugins.cisco_meraki.lib.utils import check_last_reported_ts
from cmk.rulesets.v1.form_specs import SimpleLevelsConfigModel

type Section = DeviceStatus


class PowerSupply(BaseModel, frozen=True):
    slot: int
    model: str
    serial: str
    status: str


class Components(BaseModel, frozen=True):
    power_supplies: list[PowerSupply] = Field(alias="powerSupplies")


class DeviceStatus(BaseModel, frozen=True):
    status: str
    last_reported: datetime = Field(alias="lastReportedAt")
    components: PossiblyMissing[Components] = None

    @computed_field
    @property
    def power_supplies(self) -> dict[str, PowerSupply]:
        if not self.components:
            return {}
        return {str(ps.slot): ps for ps in self.components.power_supplies}


def parse_device_status(string_table: StringTable) -> Section | None:
    match string_table:
        case [[payload]] if payload:
            return DeviceStatus.model_validate(json.loads(payload)[0])
        case _:
            return None


agent_section_cisco_meraki_org_device_status = AgentSection(
    name="cisco_meraki_org_device_status",
    parse_function=parse_device_status,
)


def discover_device_status(section: Section) -> DiscoveryResult:
    yield Service()


_STATUS_MAP = {
    "online": State.OK.value,
    "alerting": State.CRIT.value,
    "offline": State.WARN.value,
    "dormant": State.WARN.value,
}


class Parameters(TypedDict, total=False):
    status_map: Mapping[str, int]
    last_reported_upper_levels: SimpleLevelsConfigModel[int]


def check_device_status(params: Parameters, section: Section) -> CheckResult:
    if (raw_state := params.get("status_map", {}).get(section.status)) is None:
        state = State(_STATUS_MAP[section.status])
    else:
        state = State(raw_state)
    yield Result(state=state, summary=f"Status: {section.status}")

    _, levels_upper = params.get("last_reported_upper_levels", ("no_levels", None))

    yield from check_last_reported_ts(
        last_reported_ts=section.last_reported.timestamp(),
        levels_upper=levels_upper,
        as_metric=True,
    )


check_plugin_cisco_meraki_org_device_status = CheckPlugin(
    name="cisco_meraki_org_device_status",
    service_name="Device Status",
    discovery_function=discover_device_status,
    check_function=check_device_status,
    check_default_parameters=Parameters(),
    check_ruleset_name="cisco_meraki_org_device_status",
)


def discover_device_status_ps(section: Section) -> DiscoveryResult:
    for slot in section.power_supplies:
        yield Service(item=slot)


def check_device_status_ps(item: str, params: Mapping[str, int], section: Section) -> CheckResult:
    if (power_supply := section.power_supplies.get(item)) is None:
        return

    if power_supply.status.lower() == "powering":
        state = State.OK
    else:
        state = State(params.get("state_not_powering", State.WARN.value))

    yield Result(state=state, summary=f"Status: {power_supply.status}")
    yield Result(state=State.OK, notice=f"Model: {power_supply.model}")
    yield Result(state=State.OK, notice=f"Serial: {power_supply.serial}")


check_plugin_cisco_meraki_org_device_status_ps = CheckPlugin(
    name="cisco_meraki_org_device_status_ps",
    service_name="Power Supply %s",
    sections=["cisco_meraki_org_device_status"],
    discovery_function=discover_device_status_ps,
    check_function=check_device_status_ps,
    check_default_parameters={},
    check_ruleset_name="cisco_meraki_org_device_status_ps",
)


def inventorize_power_supplies(section: Section) -> InventoryResult:
    for power_supply in section.power_supplies.values():
        yield TableRow(
            path=["hardware", "components", "psus"],
            key_columns={
                "index": power_supply.slot,
                "serial": power_supply.serial,
            },
            inventory_columns={
                "model": power_supply.model,
                "location": f"Slot {power_supply.slot}",
                "manufacturer": "Cisco Meraki",
            },
        )


inventory_plugin_cisco_meraki_power_supplies = InventoryPlugin(
    name="cisco_meraki_power_supplies",
    inventory_function=inventorize_power_supplies,
    sections=["cisco_meraki_org_device_status"],
)
