#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
    check_levels,
    render,
)

from cmk_addons.plugins.meraki.lib.utils import get_int, load_json

# sample string_table
__appliance_uplinks = [
    {
        'highAvailability': {
            'enabled': False,
            'role': 'primary'
        },
        'lastReportedAt': '2023-11-05T08:18:21Z',
        'model': 'MX68',
        'networkId': 'L_6209337986237261234',
        'networkName': 'NetworkName',
        'serial': 'Q2KY-DCBA-ABCD',
        'uplinks': [
            {
                'gateway': '192.168.10.1',
                'interface': 'wan1',
                'ip': '192.168.10.2',
                'ipAssignedBy': 'static',
                'primaryDns': '192.168.10.1',
                'publicIp': '20.197.135.251',
                'secondaryDns': '9.9.9.9',
                'status': 'active',
                'received': 52320006,  # bytes
                'sent': 52928038,  # bytes
            },
            {
                'gateway': '192.168.5.100',
                'interface': 'wan2',
                'ip': '192.168.5.236',
                'ipAssignedBy': 'dhcp',
                'primaryDns': '192.168.5.100',
                'publicIp': '20.151.100.109',
                'secondaryDns': '0.0.0.0',
                'status': 'active'
            }
        ]
    }
]

_LAST_REPORTED_AT = '%Y-%m-%dT%H:%M:%SZ'


@dataclass(frozen=True)
class ApplianceUplink:
    gateway: str | None
    interface: str | None
    ip: str | None
    ip_assigned_by: str | None
    primary_dns: str | None
    public_ip: str | None
    received: int | None
    secondary_dns: str | None
    sent: int | None
    status: str | None

    @classmethod
    def parse(cls, uplink: Mapping[str: object]):
        return cls(
            gateway=str(uplink['gateway']) if uplink.get('gateway') is not None else None,
            interface=str(uplink['interface']) if uplink.get('interface') is not None else None,
            ip=str(uplink['ip']) if uplink.get('ip') is not None else None,
            ip_assigned_by=str(uplink['ipAssignedBy']) if uplink.get('ipAssignedBy') is not None else None,
            primary_dns=str(uplink['primaryDns']) if uplink.get('primaryDns') is not None else None,
            public_ip=str(uplink['publicIp']) if uplink.get('publicIp') is not None else None,
            received=get_int(uplink.get('received')),
            secondary_dns=str(uplink['secondaryDns']) if uplink.get('secondaryDns') is not None else None,
            sent=get_int(uplink.get('sent')),
            status=str(uplink['status']) if uplink.get('status') is not None else None,
        )


@dataclass(frozen=True)
class ApplianceUplinkHA:
    enabled: bool | None
    role: str | None

    @classmethod
    def parse(cls, high_availability: Mapping[str: object]):
        return cls(
            enabled=bool(high_availability['enabled']) if high_availability.get('enabled') is not None else None,
            role=str(high_availability['role']) if high_availability.get('role') is not None else None,
        )


@dataclass(frozen=True)
class Appliance:
    high_availability: ApplianceUplinkHA | None
    last_reported_at: datetime | None
    model: str | None
    network_name: str | None
    serial: str | None
    uplinks: Mapping[str, ApplianceUplink] | None

    @classmethod
    def parse(cls, appliance: Mapping[str: object]):
        return cls(
            high_availability=ApplianceUplinkHA.parse(appliance['highAvailability']) if appliance.get(
                'highAvailability') is not None else None,
            last_reported_at=datetime.strptime(appliance['lastReportedAt'], _LAST_REPORTED_AT) if appliance[
                'lastReportedAt'] else None,
            model=str(appliance['model']) if appliance.get('model') is not None else None,
            network_name=str(appliance['networkName']) if appliance.get('networkName') is not None else None,
            serial=str(appliance['serial']) if appliance.get('serial') is not None else None,
            uplinks={uplink['interface']: ApplianceUplink.parse(uplink) for uplink in appliance.get('uplinks', [])},
        )


def parse_appliance_uplinks(string_table: StringTable) -> Appliance | None:
    json_data = load_json(string_table)
    return Appliance.parse(json_data[0])


agent_section_cisco_meraki_org_appliance_uplinks = AgentSection(
    name='cisco_meraki_org_appliance_uplinks',
    parse_function=parse_appliance_uplinks,
)


def discover_appliance_uplinks(section: Appliance) -> DiscoveryResult:
    for uplink in section.uplinks.keys():
        yield Service(item=uplink)


_STATUS_MAP = {
    'active': 0,
    'failed': 2,
    'not_connected': 1,
    'ready': 0,
    'connecting': 1,
}
_TIMESPAN = 60


def render_network_bandwidth_bits(value: int) -> str:
    return render.networkbandwidth(value/8)


def check_appliance_uplinks(item: str, params: Mapping[str, any], section: Appliance) -> CheckResult:
    if (uplink := section.uplinks.get(item)) is None:
        return None

    if params.get('status_map'):
        _STATUS_MAP.update(params['status_map'])
    _STATUS_MAP['not connected'] = _STATUS_MAP['not_connected']  # can not use 'nor connected' in params anymore :-(

    yield Result(state=State(_STATUS_MAP.get(uplink.status, 3)), summary=f'Status: {uplink.status}')
    if uplink.ip:
        yield Result(state=State.OK, summary=f'IP: {uplink.ip}')
    if uplink.public_ip:
        yield Result(state=State.OK, summary=f'Public IP: {uplink.public_ip}')
    yield Result(state=State.OK, notice=f'Network: {section.network_name}')

    if params.get('show_traffic') and uplink.status in ['active']:  # we can only have traffic, if uplink is connected
        if uplink.received:  # and params.get('show_traffic'):
            value = uplink.received * 8 / _TIMESPAN  # Bits / Timespan
            yield from check_levels(
                value=value,  # Bits
                label='In',
                metric_name='if_in_bps',
                render_func=render_network_bandwidth_bits, # Bytes
            )

        if uplink.sent:  # and params.get('show_traffic'):
            value = uplink.sent * 8 / _TIMESPAN  # Bits / Timespan
            yield from check_levels(
                value=value,  # Bits
                label='Out',
                metric_name='if_out_bps',
                render_func=render_network_bandwidth_bits, # Bytes
            )

    # not needed, will show in device status (?)
    # yield from check_last_reported_ts(last_reported_ts=section.last_reported_at.timestamp())

    # not sure if this is usefully, need system with H/A enabled=True to check
    yield Result(state=State.OK, notice=f'H/A enabled: {section.high_availability.enabled}')
    yield Result(state=State.OK, notice=f'H/A role: {section.high_availability.role}')

    if uplink.gateway:
        yield Result(state=State.OK, notice=f'Gateway: {uplink.gateway}')
    if uplink.ip_assigned_by:
        yield Result(state=State.OK, notice=f'IP assigned by: {uplink.ip_assigned_by}')
    if uplink.primary_dns:
        yield Result(state=State.OK, notice=f'Primary DNS: {uplink.primary_dns}')
    if uplink.secondary_dns:
        yield Result(state=State.OK, notice=f'Secondary DNS: {uplink.secondary_dns}')


check_plugin_cisco_meraki_org_appliance_uplinks = CheckPlugin(
    name='cisco_meraki_org_appliance_uplinks',
    service_name='Uplink %s',
    discovery_function=discover_appliance_uplinks,
    check_function=check_appliance_uplinks,
    check_default_parameters={},
    check_ruleset_name='cisco_meraki_org_appliance_uplinks',
)
