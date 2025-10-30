#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# enhancements by thl-cmk[at]outlook[dot]com, https://thl-cmk.hopto.org
# - made device status configurable via WATO
# - added last_reported as check_levels, levels_upper can be configured via WATO
# - added power supply's
# - added unknown components (for discovery)
# - removed device offline check from device status discovery function
# - added power supplys to inventory (hardware -> physical components -> power supplys
# - changed item from "Cisco Meraki Device" Status to "Device Status" -> we know this is a Meraki device ;-)
#
# 2023-11-09: fixed crash if no powersupply in components
# 2023-11-19: fixed crash in inventory if no powersupply in components
# 2024-06-24: fixed don't output empty model/serial for poer supply
# 2025-03-30: moved to check APIv2
# 2025-05-18: fixed handling of time zone in _parse_last_reported (ThX to cultureunrented@forum.checkmk.com)

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone

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

from cmk_addons.plugins.meraki.lib.utils import MerakiAPIData, check_last_reported_ts, load_json


@dataclass(frozen=True)
class Poe:
    maximum: int
    unit: str


@dataclass(frozen=True)
class PowerSupply:
    slot: str
    model: str
    serial: str
    status: str
    poe: Poe | None


@dataclass(frozen=True)
class DeviceStatus:
    status: str
    last_reported: datetime | None
    power_supplys: Sequence[PowerSupply] | None
    unknown_components: Mapping | None

    @classmethod
    def parse(cls, row: MerakiAPIData) -> "DeviceStatus":
        return cls(
            status=str(row["status"]),
            last_reported=cls._parse_last_reported(str(row["lastReportedAt"])),
            power_supplys=cls._parse_powersupplies(_components=row['components']) if row.get('components') else [],
            unknown_components=row.get('components') if row.get('components', {}) != {} else None,
        )

    @staticmethod
    def _parse_last_reported(raw_last_reported: str) -> datetime | None:
        try:
            return datetime.strptime(raw_last_reported, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    @staticmethod
    def _parse_powersupplies(_components: Mapping[str, any] | None) -> Sequence[PowerSupply] | None:
        def _parse_poe(_poe: Mapping[str, any]) -> Poe | None:
            try:
                return Poe(
                    maximum=_poe['maximum'],
                    unit=_poe['unit'],
                ) if _poe['maximum'] > 0 else None
            except KeyError:
                return None

        power_supplys = _components.get('powerSupplies', [])
        try:
            _components.pop('powerSupplies')
        except KeyError:
            pass

        return [PowerSupply(
            model=power_supply['model'],
            slot=str(power_supply['slot']),
            serial=power_supply['serial'],
            status=power_supply['status'],
            poe=_parse_poe(power_supply['poe'])
        ) for power_supply in power_supplys]


def parse_device_status(string_table: StringTable) -> DeviceStatus | None:
    return DeviceStatus.parse(loaded_json[0]) if (loaded_json := load_json(string_table)) else None


agent_section_cisco_meraki_org_device_status = AgentSection(
    name="cisco_meraki_org_device_status",
    parse_function=parse_device_status,
)


def discover_device_status(section: DeviceStatus | None) -> DiscoveryResult:
    yield Service()


_STATUS_MAP = {
    "online": 0,  # changed to int to be compatible with wato
    "alerting": 2,
    "offline": 1,
    "dormant": 1,  # TODO not sure -> now configurable via WATO
}


def check_device_status(params: Mapping[str, any], section: DeviceStatus | None) -> CheckResult:
    if not section:
        return

    if params.get('status_map'):
        _STATUS_MAP.update(params['status_map'])

    yield Result(
        state=State(_STATUS_MAP.get(section.status, 3)),
        summary=f"Status: {section.status}",
    )

    if section.last_reported is not None:
        yield from check_last_reported_ts(
            last_reported_ts=section.last_reported.timestamp(),
            levels_upper=params.get('last_reported_upper_levels', None)
        )


check_plugin_cisco_meraki_org_device_status = CheckPlugin(
    name="cisco_meraki_org_device_status",
    service_name="Device Status",
    discovery_function=discover_device_status,
    check_function=check_device_status,
    check_default_parameters={},
    check_ruleset_name='cisco_meraki_device_status',
)


def discover_device_status_ps(section: DeviceStatus | None) -> DiscoveryResult | None:
    if section.power_supplys:
        for power_supply in section.power_supplys:
            yield Service(item=power_supply.slot)


def check_device_status_ps(item: str, params: Mapping[str, any], section: DeviceStatus | None) -> CheckResult:
    power_supply = None
    for power_supply in section.power_supplys:
        if power_supply.slot == item:
            break

    if power_supply:
        if power_supply.status.lower() == 'powering':
            yield Result(state=State.OK, summary=f'Status: {power_supply.status}')
        else:
            yield Result(
                state=State(params.get('state_not_powering', 1)),
                summary=f'Status: {power_supply.status}',
            )
        if power_supply.model:
            yield Result(state=State.OK, summary=f'Model: {power_supply.model}')
        if power_supply.serial:
            yield Result(state=State.OK, summary=f'Serial: {power_supply.serial}')
        if power_supply.poe:
            yield Result(
                state=State.OK,
                summary=f'PoE: {power_supply.poe.maximum} {power_supply.poe.unit} maximum'
            )


check_plugin_cisco_meraki_org_device_status_ps = CheckPlugin(
    name="cisco_meraki_org_device_status_ps",
    service_name="Power supply slot %s",
    sections=['cisco_meraki_org_device_status'],
    discovery_function=discover_device_status_ps,
    check_function=check_device_status_ps,
    check_default_parameters={},
    check_ruleset_name='cisco_meraki_device_status_ps',
)


def discover_device_status_unknown_components(section: DeviceStatus | None) -> DiscoveryResult | None:
    if section.unknown_components:
        yield Service()


def check_device_status_unknown_components(section: DeviceStatus | None) -> CheckResult:
    yield Result(
        state=State.UNKNOWN,
        summary=f'{str(list(section.unknown_components.keys()))}',
        details=f'{section}',
    )


check_plugin_cisco_meraki_org_device_status_unknown_components = CheckPlugin(
    name="cisco_meraki_org_device_status_unknown_components",
    service_name="Unknown components",
    sections=['cisco_meraki_org_device_status'],
    discovery_function=discover_device_status_unknown_components,
    check_function=check_device_status_unknown_components,
)


#
# inventory of device components overview
#
def inventory_powersupplys(section: DeviceStatus | None) -> InventoryResult:
    path = ['hardware', 'components', 'power_supplys']
    index = 1
    for power_supply in section.power_supplys:
        yield TableRow(
            path=path,
            key_columns={'serial': power_supply.serial},
            inventory_columns={
                'model': power_supply.model,
                'location': f'Slot {power_supply.slot}',
                'index': index
            }
        )
        index += 1


inventory_plugin_cisco_meraki_power_supplys = InventoryPlugin(
    name="cisco_meraki_power_supplys",
    inventory_function=inventory_powersupplys,
    sections=['cisco_meraki_org_device_status']
)
