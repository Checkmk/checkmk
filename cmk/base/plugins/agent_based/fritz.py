#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Sequence
from .agent_based_api.v1 import register, type_defs
from .utils import interfaces

Section = Mapping[str, str]


def parse_fritz(string_table: type_defs.AgentStringTable) -> Section:
    """
    >>> from pprint import pprint
    >>> pprint(parse_fritz([
    ... ['VersionOS', '137.06.83'], ['VersionDevice', 'AVM', 'FRITZ!Box', '7412', '(UI)'],
    ... ['NewVoipDNSServer1', '217.237.148.102'], ['NewDNSServer2', '217.237.151.115'],
    ... ['NewDNSServer1', '217.237.148.102'], ['NewVoipDNSServer2', '217.237.151.115'],
    ... ['NewIdleDisconnectTime', '0'], ['NewLayer1DownstreamMaxBitRate', '25088000'],
    ... ['NewWANAccessType', 'DSL'], ['NewByteSendRate', '197'], ['NewPacketReceiveRate', '0'],
    ... ['NewConnectionStatus', 'Connected'], ['NewRoutedBridgedModeBoth', '1'], ['NewUptime', '1'],
    ... ['NewTotalBytesReceived', '178074787'], ['NewPacketSendRate', '0'],
    ... ['NewPhysicalLinkStatus', 'Up'], ['NewLinkStatus', 'Up'],
    ... ['NewLayer1UpstreamMaxBitRate', '5056000'], ['NewTotalBytesSent', '40948982'],
    ... ['NewLastConnectionError', 'ERROR_NONE'], ['NewAutoDisconnectTime', '0'],
    ... ['NewExternalIPAddress', '217.235.84.223'], ['NewLinkType', 'PPPoE'],
    ... ['NewByteReceiveRate', '0'], ['NewUpnpControlEnabled', '1']]))
    {'NewAutoDisconnectTime': '0',
     'NewByteReceiveRate': '0',
     'NewByteSendRate': '197',
     'NewConnectionStatus': 'Connected',
     'NewDNSServer1': '217.237.148.102',
     'NewDNSServer2': '217.237.151.115',
     'NewExternalIPAddress': '217.235.84.223',
     'NewIdleDisconnectTime': '0',
     'NewLastConnectionError': 'ERROR_NONE',
     'NewLayer1DownstreamMaxBitRate': '25088000',
     'NewLayer1UpstreamMaxBitRate': '5056000',
     'NewLinkStatus': 'Up',
     'NewLinkType': 'PPPoE',
     'NewPacketReceiveRate': '0',
     'NewPacketSendRate': '0',
     'NewPhysicalLinkStatus': 'Up',
     'NewRoutedBridgedModeBoth': '1',
     'NewTotalBytesReceived': '178074787',
     'NewTotalBytesSent': '40948982',
     'NewUpnpControlEnabled': '1',
     'NewUptime': '1',
     'NewVoipDNSServer1': '217.237.148.102',
     'NewVoipDNSServer2': '217.237.151.115',
     'NewWANAccessType': 'DSL',
     'VersionDevice': 'AVM FRITZ!Box 7412 (UI)',
     'VersionOS': '137.06.83'}
    """
    return {line[0]: ' '.join(line[1:]) for line in string_table if len(line) > 1}


register.agent_section(
    name="fritz",
    parse_function=parse_fritz,
)


#
# WAN Interface Check
#
def _section_to_interface(section: Section) -> interfaces.Section:
    """
    >>> from pprint import pprint
    >>> pprint(_section_to_interface({
    ... 'NewLayer1DownstreamMaxBitRate': '25088000',
    ... 'NewLinkStatus': 'Up',
    ... 'NewTotalBytesReceived': '178074787',
    ... 'NewTotalBytesSent': '40948982',
    ... }))
    [Interface(index='0', descr='WAN', alias='WAN', type='6', speed=25088000, oper_status='1', in_octets=178074787, in_ucast=0, in_mcast=0, in_bcast=0, in_discards=0, in_errors=0, out_octets=40948982, out_ucast=0, out_mcast=0, out_bcast=0, out_discards=0, out_errors=0, out_qlen=0, phys_address='', oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None)]
    >>> pprint(_section_to_interface({
    ... 'NewLayer1DownstreamMaxBitRate': '25088000',
    ... 'NewTotalBytesReceived': '178074787',
    ... 'NewTotalBytesSent': '40948982',
    ... }))
    [Interface(index='0', descr='WAN', alias='WAN', type='6', speed=25088000, oper_status='4', in_octets=178074787, in_ucast=0, in_mcast=0, in_bcast=0, in_discards=0, in_errors=0, out_octets=40948982, out_ucast=0, out_mcast=0, out_bcast=0, out_discards=0, out_errors=0, out_qlen=0, phys_address='', oper_status_name='unknown', speed_as_text='', group=None, node=None, admin_status=None)]
    """
    link_stat = section.get('NewLinkStatus')
    if not link_stat:
        oper_status = '4'
    elif link_stat == 'Up':
        oper_status = '1'
    else:
        oper_status = '2'
    return [
        interfaces.Interface(
            index='0',
            descr='WAN',
            alias='WAN',
            type='6',
            speed=int(section.get('NewLayer1DownstreamMaxBitRate', 0)),
            oper_status=oper_status,
            in_octets=int(section.get('NewTotalBytesReceived', 0)),
            out_octets=int(section.get('NewTotalBytesSent', 0)),
        )
    ]


def discover_fritz_wan_if(
    params: Sequence[type_defs.Parameters],
    section: Section,
) -> type_defs.DiscoveryResult:
    yield from interfaces.discover_interfaces(
        params,
        _section_to_interface(section),
    )


def check_fritz_wan_if(
    item: str,
    params: type_defs.Parameters,
    section: Section,
) -> type_defs.CheckResult:
    params_updated = dict(params)
    params_updated.update({
        'assumed_speed_in': int(section['NewLayer1DownstreamMaxBitRate']),
        'assumed_speed_out': int(section['NewLayer1UpstreamMaxBitRate']),
        'unit': 'bit',
    })
    yield from interfaces.check_multiple_interfaces(
        item,
        type_defs.Parameters(params_updated),
        _section_to_interface(section),
    )


register.check_plugin(
    name="fritz_wan_if",
    sections=["fritz"],
    service_name="Interface %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type="all",
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=discover_fritz_wan_if,
    check_ruleset_name="if",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=check_fritz_wan_if,
)
