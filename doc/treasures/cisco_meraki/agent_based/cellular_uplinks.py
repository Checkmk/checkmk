#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2023-11-13
# File  : cellular_uplinks.py (check plugin)

# 2024-04-27: made data parsing more robust
# 2024-06-29: refactored for CMK 2.3
#             moved parse functions to class methods
#             changed service name from 'Cellular uplink' to 'Uplink'
# 2024-06-30: renamed from cisco_meraki_org_cellular_uplinks.py in to cellular_uplinks.py

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

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
    render,
)

from cmk_addons.plugins.meraki.lib.utils import get_int, load_json

__cellular_uplinks = [
    {
        'highAvailability': {
            'enabled': False,
            'role': 'primary'
        },
        'lastReportedAt': '2023-11-13T19:52:06Z',
        'model': 'MG41',
        'networkId': 'L_575897802350012343',
        'serial': 'QQQQ-XXXX-ZZZZ',
        'uplinks': [
            {
                'apn': 'apn.name',
                'connectionType': 'lte',
                'dns1': None,
                'dns2': None,
                'gateway': None,
                'iccid': '89492027206012345518',
                'interface': 'cellular',
                'ip': None,
                'model': 'integrated',
                'provider': 'provider.name',
                'publicIp': '2.3.4.5',
                'signalStat': {
                    'rsrp': '-111',
                    'rsrq': '-8'
                },
                'signalType': None,
                'status': 'active'
            }
        ]
    }
]

_LAST_REPORTED_AT = '%Y-%m-%dT%H:%M:%SZ'


@dataclass(frozen=True)
class CellularUplink:
    apn: str | None
    connection_type: str | None
    dns1: str | None
    dns2: str | None
    gateway: str | None
    iccid: str | None
    interface: str | None
    ip: str | None
    model: str | None
    provider: str | None
    public_ip: str | None
    received: int | None
    rsrp: int | None
    rsrq: int | None
    sent: int | None
    signal_type: str | None
    status: str | None

    @classmethod
    def parse(cls, uplink: Mapping[str, object]):
        return cls(
            apn=str(uplink['apn']) if uplink.get('apn') is not None else None,
            connection_type=str(uplink['connectionType']) if uplink.get('connectionType') is not None else None,
            dns1=str(uplink['dns1']) if uplink.get('dns1') is not None else None,
            dns2=str(uplink['dns2']) if uplink.get('dns2') is not None else None,
            gateway=str(uplink['gateway']) if uplink.get('gateway') is not None else None,
            iccid=str(uplink['iccid']) if uplink.get('iccid') is not None else None,
            interface=str(uplink['interface']) if uplink.get('interface') is not None else None,
            ip=str(uplink['ip']) if uplink.get('ip') is not None else None,
            model=str(uplink['model']) if uplink.get('model') is not None else None,
            provider=str(uplink['provider']) if uplink.get('provider') is not None else None,
            public_ip=str(uplink['publicIp']) if uplink.get('publicIp') is not None else None,
            signal_type=str(uplink['signalType']) if uplink.get('signalType') is not None else None,
            status=str(uplink['status']) if uplink.get('status') is not None else None,
            rsrp=get_int(uplink.get('signalStat', {}).get('rsrp')),
            rsrq=get_int(uplink.get('signalStat', {}).get('rsrq')),
            received=get_int(uplink.get('received')),
            sent=get_int(uplink.get('sent')),
        )


@dataclass(frozen=True)
class CellularUplinkHA:
    enabled: bool | None
    role: str | None

    @classmethod
    def parse(cls, high_availability: Mapping[str, object]):
        return cls(
            enabled=bool(high_availability['enabled']) if high_availability.get('enabled') is not None else None,
            role=str(high_availability['role']) if high_availability.get('enabled') is not None else None,
        )


@dataclass(frozen=True)
class CellularGateway:
    high_availability: CellularUplinkHA | None
    last_reported_at: datetime | None
    model: str | None
    # network_name: str
    serial: str | None
    uplinks: Mapping[str, CellularUplink] | None

    @classmethod
    def parse(cls, cellular_gateway):
        return cls(
            serial=str(cellular_gateway['serial']) if cellular_gateway.get('serial') is not None else None,
            model=str(cellular_gateway['model']) if cellular_gateway.get('model') is not None else None,
            last_reported_at=datetime.strptime(
                cellular_gateway['lastReportedAt'], _LAST_REPORTED_AT) if cellular_gateway.get(
                'lastReportedAt'
            ) is not None else None,
            # network_name=str(json_data['networkName']) if json_data.get('networkName') is not None else None,
            high_availability=CellularUplinkHA.parse(cellular_gateway.get('highAvailability', {})),
            uplinks={
                uplink['interface']: CellularUplink.parse(uplink) for uplink in cellular_gateway.get('uplinks', [])
            },
        )


def parse_cellular_uplinks(string_table: StringTable) -> CellularGateway | None:
    json_data = load_json(string_table)
    json_data = json_data[0]
    return CellularGateway.parse(json_data)


agent_section_cisco_meraki_org_cellular_uplinks = AgentSection(
    name='cisco_meraki_org_cellular_uplinks',
    parse_function=parse_cellular_uplinks,
)


def discover_cellular_uplinks(section: CellularGateway) -> DiscoveryResult:
    for uplink in section.uplinks.keys():
        yield Service(item=uplink)


def check_cellular_uplinks(item: str, params: Mapping[str, any], section: CellularGateway) -> CheckResult:
    if (uplink := section.uplinks.get(item)) is None:
        return

    if uplink.status not in ['active']:
        yield Result(state=State(params.get('status_not_active', 1)), summary=f'Status: {uplink.status}')
    else:
        yield Result(state=State.OK, summary=f'Status: {uplink.status}')
    yield Result(state=State.OK, notice=f'IP: {uplink.ip}')
    yield Result(state=State.OK, notice=f'APN: {uplink.apn}')
    yield Result(state=State.OK, notice=f'Provider: {uplink.provider}')
    yield Result(state=State.OK, summary=f'Public IP: {uplink.public_ip}')
    yield Result(state=State.OK, summary=f'Connection type: {uplink.connection_type}')
    yield Result(state=State.OK, notice=f'ICCID: {uplink.iccid}')
    yield Result(state=State.OK, notice=f'Signal type: {uplink.signal_type}')

    # yield Result(state=State.OK, notice=f'Network: {section.network_name}')

    if uplink.rsrp:
        yield Result(state=State.OK, summary=f'RSRP: {uplink.rsrp} dBm')

    if uplink.rsrp:
        yield Result(state=State.OK, summary=f'RSRQ: {uplink.rsrq} dB')

    if uplink.received:
        yield Result(state=State.OK, summary=f'In: {render.networkbandwidth(uplink.received)}')
        yield Metric(name='if_in_bps', value=uplink.received * 8)

    if uplink.sent:
        yield Result(state=State.OK, summary=f'Out: {render.networkbandwidth(uplink.sent)}')
        yield Metric(name='if_out_bps', value=uplink.sent * 8)

    # not needed, will show in device status
    # yield from check_last_reported_ts(last_reported_ts=section.last_reported_at.timestamp())

    # not sure if this is usefully, need system with H/A enabled=True to check
    yield Result(state=State.OK, notice=f'H/A enabled: {section.high_availability.enabled}')
    yield Result(state=State.OK, notice=f'H/A role: {section.high_availability.role}')

    yield Result(state=State.OK, notice=f'Gateway: {uplink.gateway}')
    # yield Result(state=State.OK, notice=f'IP assigned by: {uplink.ip_assigned_by}')
    yield Result(state=State.OK, notice=f'DNS 1: {uplink.dns1}')
    yield Result(state=State.OK, notice=f'DNS 2: {uplink.dns2}')


check_plugin_cisco_meraki_org_cellular_uplinks = CheckPlugin(
    name='cisco_meraki_org_cellular_uplinks',
    service_name='Uplink %s',
    discovery_function=discover_cellular_uplinks,
    check_function=check_cellular_uplinks,
    check_default_parameters={},
    check_ruleset_name='cisco_meraki_org_cellular_uplinks',
)
