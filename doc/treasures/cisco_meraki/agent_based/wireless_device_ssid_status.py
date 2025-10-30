#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2023-11-11
# File  : wireless_device_status.py (check plugin)

# 2024-04-27: made data parsing more robust
# 2024-06-23: fixed crash on empty json_data
#             moved data parsing in to SSID class
# 2024-06-30: renamed from cisco_meraki_org_wireless_device_status.py int to wireless_device_ssid_status.py
# 2024-07-13: fixed crash on missing metrics (device dormant) ThX to Leon Buhleier
# 2024-08-07: fixed crash on missing power value (unit only) ThX to Leon Buhleier
# 2024-09-12: fixed missing SSID 0 ThX to Andreas Doehler
# 2024-12-13: fixed crash if no valid data received (json_data = [[]])

from collections.abc import Mapping
from dataclasses import dataclass

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
from cmk_addons.plugins.meraki.lib.utils import get_int, load_json


@dataclass(frozen=True)
class SSID:
    band: str | None
    broadcasting: bool | None
    bssid: str | None
    channel: int | None
    channel_width: str | None
    enabled: bool | None
    name: str | None
    number: int | None
    power: str | None
    visible: bool | None

    @classmethod
    def parse(cls, ssid: Mapping[str: object]):
        return cls(
            band=str(ssid['band']) if ssid.get('band') is not None else None,
            broadcasting=bool(ssid['broadcasting']) if ssid.get('broadcasting') is not None else None,
            bssid=str(ssid['bssid']) if ssid.get('') is not None else None,
            channel=get_int(ssid.get('channel')),
            channel_width=str(ssid['channelWidth']) if ssid.get('channelWidth') is not None else None,
            enabled=bool(ssid['enabled']) if ssid.get('enabled') is not None else None,
            name=str(ssid['ssidName']) if ssid.get('ssidName') is not None else None,
            number=get_int(ssid.get('ssidNumber')),
            power=str(ssid['power']) if ssid.get('power') is not None else None,
            visible=bool(ssid['enabled']) if ssid.get('enabled') is not None else None,
        )


def parse_wireless_device_status(string_table: StringTable) -> Mapping[str, SSID] | None:
    json_data = load_json(string_table)
    if not (json_data := json_data[0]):
        return None

    ssids = {}
    for row in json_data.get('basicServiceSets', []):
        if row.get('ssidName') and row.get('ssidName', '').startswith('Unconfigured SSID'):
            continue  # ignore unconfigured entry's

        if (ssid_number := row.get('ssidNumber')) is None:
            continue

        item = str(ssid_number) + ' on band ' + row.get('band')

        ssids[item] = SSID.parse(row)
    return ssids


agent_section_cisco_meraki_org_wireless_device_status = AgentSection(
    name="cisco_meraki_org_wireless_device_status",
    parse_function=parse_wireless_device_status,
)

_is = {
    True: '',
    False: ' not',
}


def discover_wireless_device_status(section: Mapping[str, SSID]) -> DiscoveryResult:
    for ssid in section.keys():
        yield Service(item=ssid)


def check_wireless_device_status(
        item: str,
        params: Mapping[str, any],
        section: Mapping[str, SSID]
) -> CheckResult:
    if (ssid := section.get(item)) is None:
        return

    yield Result(state=State.OK, summary=f'Name: {ssid.name}')
    if not ssid.enabled:
        yield Result(state=State(params['state_if_not_enabled']), summary=f'is{_is[ssid.enabled]} enabled')
    else:
        yield Result(state=State.OK, summary=f'is{_is[ssid.enabled]} enabled')

        # don't show details if SSID not enabled
        yield Result(state=State.OK, notice=f'is{_is[ssid.visible]} visible')
        yield Result(state=State.OK, notice=f'is{_is[ssid.broadcasting]} broadcasting')
        yield Result(state=State.OK, notice=f'BSSID: {ssid.bssid}')
        yield Result(state=State.OK, notice=f'Band: {ssid.band}')
        yield Result(state=State.OK, summary=f'Channel: {ssid.channel}')
        yield Result(state=State.OK, summary=f'Channel width: {ssid.channel_width}')
        yield Result(state=State.OK, summary=f'Power: {ssid.power}')

        try:
            channel_width = int(ssid.channel_width.split(' ')[0]) * 1000000  # change MHz -> Hz
        except AttributeError:
            channel_width = None

        try:
            power = int(ssid.power.split(' ')[0])
        except (AttributeError, ValueError):
            power = None

        for metric, value in [
            ('channel', ssid.channel),
            ('channel_width', channel_width),
            ('signal_power', power)
        ]:
            if value is not None:
                yield Metric(name=metric, value=value)


check_plugin_cisco_meraki_org_wireless_device_status = CheckPlugin(
    name='cisco_meraki_org_wireless_device_status',
    service_name='SSID %s',
    discovery_function=discover_wireless_device_status,
    check_function=check_wireless_device_status,
    check_default_parameters={
        'state_if_not_enabled': 1,
    },
    check_ruleset_name='cisco_meraki_wireless_device_status',
)
