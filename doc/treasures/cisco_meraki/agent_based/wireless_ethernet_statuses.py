#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

# ToDo: create ruleset cisco_meraki_wireless_ethernet_statuses

from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
    render,
    InventoryPlugin,
    InventoryResult,
    TableRow,
)
from cmk_addons.plugins.meraki.lib.utils import get_int, load_json

__ethernet_port_statuses = {
    'aggregation': {
        'enabled': False,
        'speed': 1000
    },
    'name': 'AP01',
    'network': {
        'id': 'L_575897802350012343'
    },
    'ports': [
        {
            'linkNegotiation': {
                'duplex': 'full',
                'speed': 1000
            },
            'name': 'Ethernet 0',
            'poe': {
                'standard': '802.3at'
            }
        }
    ],
    'power': {
        'ac': {
            'isConnected': False
        },
        'mode': 'full',
        'poe': {
            'isConnected': True
        }
    },
    'serial': 'AAAA-BBBB-CCCC'
}


@dataclass(frozen=True)
class WirelessEthernetPortPower:
    mode: str | None
    ac: bool | None
    poe: bool | None

    @classmethod
    def parse(cls, power: Mapping[str, object]):
        return cls(
            mode=str(power['mode']) if power.get('mode') is not None else None,
            ac=bool(power['ac']['isConnected']) if power.get('ac', {}).get('isConnected') is not None else None,
            poe=bool(power['poe']['isConnected']) if power.get('poe', {}).get('isConnected') is not None else None,
        )


@dataclass(frozen=True)
class WirelessEthernetPort:
    name: str | None
    poe: str | None
    duplex: str | None
    speed: int | None
    power: WirelessEthernetPortPower | None

    @classmethod
    def parse(cls, port: Mapping[str, object], power: WirelessEthernetPortPower):
        return cls(
            name=str(port['name']) if port.get('name') is not None else None,
            power=power,
            duplex=port['linkNegotiation']['duplex'] if port.get('linkNegotiation', {}).get(
                'duplex') is not None else None,
            # changed to bit/s
            speed=int(port['linkNegotiation']['speed']) * 125000 if get_int(port.get('linkNegotiation', {}).get(
                'speed')) else None,
            poe=str(port['poe']['standard']) if port.get('poe', {}).get('standard') is not None else None,
        )


# _is_connected = {
#     True: 'Yes',
#     False: 'No',
# }


def parse_wireless_ethernet_statuses(string_table: StringTable) -> Mapping[str, WirelessEthernetPort] | None:
    json_data = load_json(string_table)
    json_data = json_data[0]

    power = WirelessEthernetPortPower.parse(json_data['power']) if json_data.get('power') is not None else None

    return {port['name']: WirelessEthernetPort.parse(port, power) for port in json_data.get('ports', [])}


agent_section_cisco_meraki_org_wireless_ethernet_statuses = AgentSection(
    name="cisco_meraki_org_wireless_ethernet_statuses",
    parse_function=parse_wireless_ethernet_statuses,
)


def discover_wireless_ethernet_statuses(section: Mapping[str, WirelessEthernetPort]) -> DiscoveryResult:
    for port in section.keys():
        yield Service(item=port, parameters={'speed': section[port].speed})


def check_wireless_ethernet_statuses(
        item: str,
        params: Mapping[str, any],
        section: Mapping[str, WirelessEthernetPort]
) -> CheckResult:
    def _status_changed(is_state: str, was_state: str, state: int, message: str):
        if is_state != was_state:
            yield Result(state=State(state), notice=f'{message}: is {is_state}, was {was_state}')

    if (port := section.get(item)) is None:
        return None

    if port.speed:
        yield from _status_changed(
            is_state=render.nicspeed(port.speed),
            was_state=render.nicspeed(params['speed']),
            message='Speed changed',
            state=params['state_speed_change']
        )
        yield Result(state=State.OK, summary=f'Speed: {render.nicspeed(port.speed)}')
    else:
        yield Result(state=State(params['state_no_speed']), summary=f'Speed: N/A')

    if port.duplex == 'full':
        yield Result(state=State.OK, summary=f'Duplex: {port.duplex}')
    else:
        yield Result(state=State(params['state_not_full_duplex']), summary=f'Duplex: {port.duplex}')

    if port.power.mode == 'full':
        yield Result(state=State.OK, summary=f'Power mode: {port.power.mode}')
    else:
        yield Result(state=State(params['state_not_on_fill_power']), summary=f'Power mode: {port.power.mode}')

    if port.power.ac:
        yield Result(state=State.OK, summary=f'AC is connected')
    else:
        yield Result(state=State.OK, summary=f'AC is not connected')

    if port.power.poe:
        yield Result(state=State.OK, summary=f'PoE is connected')
    else:
        yield Result(state=State.OK, summary=f'PoE is not connected')

    yield Result(state=State.OK, summary=f'PoE standard: {port.poe}')


check_plugin_cisco_meraki_org_wireless_ethernet_statuses = CheckPlugin(
    name='cisco_meraki_org_wireless_ethernet_statuses',
    service_name='Interface %s',
    discovery_function=discover_wireless_ethernet_statuses,
    check_function=check_wireless_ethernet_statuses,
    check_default_parameters={
        'state_not_on_fill_power': 1,
        'state_not_full_duplex': 1,
        'state_no_speed': 1,
        'state_speed_change': 1,
    },
    # check_ruleset_name='cisco_meraki_wireless_ethernet_statuses',
)


def inventory_meraki_wireless_ethernet(section: Mapping[str, WirelessEthernetPort]) -> InventoryResult:
    for port in section.values():
        yield TableRow(
            path=['networking', 'interfaces'],
            key_columns={
                "index": port.name.split(' ')[-1],
            },
            inventory_columns={
                # 'alias': port.name,
                # 'description': port.name,
                'name': port.name,
                'admin_status': 1,
                'oper_status': 1,
                **({'speed': render.nicspeed(port.speed)} if port.speed is not None else {}),
                'port_type': 6,
            },
        )


inventory_plugin_inv_meraki_wireless_ethernet = InventoryPlugin(
    name='inv_meraki_wireless_ethernet',
    sections=['cisco_meraki_org_wireless_ethernet_statuses'],
    inventory_function=inventory_meraki_wireless_ethernet,
)
