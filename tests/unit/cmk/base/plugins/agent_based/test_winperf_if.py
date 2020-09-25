#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import suppress
import pytest  # type: ignore[import]
from testlib import get_value_store_fixture
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResults,
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State as state,
    type_defs,
)
from cmk.base.plugins.agent_based import winperf_if
from cmk.base.plugins.agent_based.utils import interfaces

value_store_fixture = get_value_store_fixture(interfaces)


@pytest.mark.parametrize("string_table, settings, items", [
    ([], {}, []),
    ([[u'1527487554.76', u'510']], {}, []),
    (
        [
            ['123', '456', '789'],
            ['1', 'instances:', 'A_B-C_1'],
            [u'-122', u'29370873405', u'5887351577', u'0', u'0', u'bulk_count'],
            [u'-110', u'5692885', u'5153077', u'0', u'0', u'bulk_count'],
            [u'-244', u'5018312', u'4921974', u'0', u'0', u'bulk_count'],
            [u'-58', u'674573', u'231103', u'0', u'0', u'bulk_count'],
            [u'10', u'10000000000', u'10000000000', u'100000', u'100000', u'large_rawcount'],
            [u'-246', u'20569013293', u'5685847946', u'0', u'0', u'bulk_count'],
            [u'14', u'4961765', u'4425455', u'0', u'0', u'bulk_count'],
            [u'16', u'4447', u'490897', u'0', u'0', u'bulk_count'],
            [u'18', u'52100', u'5622', u'0', u'0', u'large_rawcount'],
            [u'20', u'0', u'0', u'0', u'0', u'large_rawcount'],
            [u'22', u'0', u'0', u'0', u'0', u'large_rawcount'],
            [u'-4', u'8801860112', u'201503631', u'0', u'0', u'bulk_count'],
            [u'26', u'673929', u'230448', u'0', u'0', u'bulk_count'],
            [u'28', u'644', u'655', u'0', u'0', u'bulk_count'],
            [u'30', u'0', u'0', u'0', u'0', u'large_rawcount'],
            [u'32', u'0', u'0', u'0', u'0', u'large_rawcount'],
            [u'34', u'0', u'0', u'0', u'0', u'large_rawcount'],
            [u'1086', u'0', u'0', u'0', u'0', u'large_rawcount'],
            [u'1088', u'1', u'0', u'0', u'0', u'large_rawcount'],
            [u'1090', u'3734320', u'4166703', u'0', u'0', u'bulk_count'],
            [u'1092', u'0', u'0', u'0', u'0', u'bulk_count'],
            [u'1094', u'22618', u'22618', u'22618', u'22618', u'large_rawcount'],
            [
                u'Node', u'MACAddress', u'Name', u'NetConnectionID', u'NetConnectionStatus',
                u'Speed', u'GUID'
            ],
            [
                u'NODE1 ', u' 00:00:00:00:00:00 ', u' A_B-C_1 ', u' Ethernet1-XYZ ', u' 2 ',
                u' 10000000000 ', u' {FOO-123-BAR}'
            ],
        ],
        {
            'discovery_single': (
                True,
                {
                    'item_appearance': 'alias',
                    'pad_portnumbers': True,
                },
            ),
        },
        ['Ethernet1-XYZ'],
    ),
    ([[u'1559837585.63', u'510', u'2929686'], [u'1', u'instances:', u'vmxnet3_Ethernet_Adapter'],
      [u'-122', u'38840302775', u'bulk_count'], [u'-110', u'206904763', u'bulk_count'],
      [u'-244', u'173589803', u'bulk_count'], [u'-58', u'33314960', u'bulk_count'],
      [u'10', u'10000000000', u'large_rawcount'], [u'-246', u'21145988302', u'bulk_count'],
      [u'14', u'36886547', u'bulk_count'], [u'16', u'136703256', u'bulk_count'],
      [u'18', u'0', u'large_rawcount'], [u'20', u'0', u'large_rawcount'],
      [u'22', u'0', u'large_rawcount'], [u'-4', u'17694314473', u'bulk_count'],
      [u'26', u'33127032', u'bulk_count'], [u'28', u'187928', u'bulk_count'],
      [u'30', u'0', u'large_rawcount'], [u'32', u'0', u'large_rawcount'],
      [u'34', u'0', u'large_rawcount'], [u'1086', u'0', u'large_rawcount'],
      [u'1088', u'0', u'large_rawcount'], [u'1090', u'0', u'bulk_count'],
      [u'1092', u'0', u'bulk_count'], [u'1094', u'0', u'large_rawcount']], {}, ['1']),
])
def test_winperf_if_netconnection_id(string_table, settings, items):
    assert [
        service.item for service in winperf_if.discover_winperf_if(
            [type_defs.Parameters({
                **interfaces.DISCOVERY_DEFAULT_PARAMETERS,
                **settings,
            })],
            winperf_if.parse_winperf_if(string_table),
        ) if isinstance(service, Service)
    ] == items


def test_winperf_if_inventory_teaming():
    assert list(
        winperf_if.discover_winperf_if(
            [
                type_defs.Parameters({
                    **interfaces.DISCOVERY_DEFAULT_PARAMETERS,
                    'discovery_single': (
                        True,
                        {
                            'item_appearance': 'descr',
                            'pad_portnumbers': True,
                        },
                    ),
                })
            ],
            winperf_if.parse_winperf_if([
                [u'1542018413.59', u'510', u'2341040'],
                [
                    u'4',
                    u'instances:',
                    u'HPE_Ethernet_1Gb_4-port_331i_Adapter__3',
                    u'HPE_Ethernet_1Gb_4-port_331i_Adapter__4',
                    u'HPE_Ethernet_1Gb_4-port_331i_Adapter',
                    u'HPE_Ethernet_1Gb_4-port_331i_Adapter__2',
                ],
                [
                    u'-122', u'201612106', u'187232778', u'200985680546908', u'969308895925',
                    u'bulk_count'
                ],
                [u'-110', u'2938459', u'2713782', u'141023109713', u'7143818358', u'bulk_count'],
                [u'-244', u'2920458', u'2695781', u'133889346630', u'9159143', u'bulk_count'],
                [u'-58', u'18001', u'18001', u'7133763083', u'7134659215', u'bulk_count'],
                [
                    u'10', u'1000000000', u'1000000000', u'1000000000', u'1000000000',
                    u'large_rawcount'
                ],
                [
                    u'-246', u'189182492', u'174803164', u'200050287945665', u'730174911',
                    u'bulk_count'
                ],
                [u'14', u'0', u'0', u'133879714188', u'131929', u'bulk_count'],
                [u'16', u'2920458', u'2695781', u'8946694', u'9027210', u'bulk_count'],
                [u'18', u'0', u'0', u'685748', u'4', u'large_rawcount'],
                [u'20', u'0', u'0', u'0', u'0', u'large_rawcount'],
                [u'22', u'0', u'0', u'0', u'0', u'large_rawcount'],
                [u'-4', u'12429614', u'12429614', u'935392601243', u'968578721014', u'bulk_count'],
                [u'26', u'0', u'0', u'7133594582', u'7134655376', u'bulk_count'],
                [u'28', u'18001', u'18001', u'168501', u'3839', u'bulk_count'],
                [u'30', u'0', u'0', u'0', u'0', u'large_rawcount'],
                [u'32', u'0', u'0', u'0', u'0', u'large_rawcount'],
                [u'34', u'0', u'0', u'0', u'0', u'large_rawcount'],
                [u'1086', u'0', u'0', u'0', u'0', u'large_rawcount'],
                [u'1088', u'0', u'0', u'0', u'0', u'large_rawcount'],
                [u'1090', u'0', u'0', u'0', u'0', u'bulk_count'],
                [u'1092', u'0', u'0', u'0', u'0', u'bulk_count'],
                [u'1094', u'0', u'0', u'0', u'0', u'large_rawcount'],
                [u'[teaming_start]'],
                [
                    u'TeamName', u'TeamingMode', u'LoadBalancingAlgorithm', u'MemberMACAddresses',
                    u'MemberNames', u'MemberDescriptions', u'Speed', u'GUID'
                ],
                [
                    u'LAN ', u'SwitchIndependent ', u'Dynamic ',
                    u'38:63:BB:44:D0:24;38:63:BB:44:D0:25', u'nic1;nic2',
                    u'HPE Ethernet 1Gb 4-port 331i Adapter;HPE Ethernet 1Gb 4-port 331i Adapter #2',
                    u'1000000000;1000000000',
                    u'{4DA62AA0-8163-459C-9ACE-95B1E729A7DD};{FEF2305A-57FD-4AEC-A817-C082565B6AA7}'
                ],
                [u'[teaming_end]'],
                [
                    u'Node', u'MACAddress', u'Name', u'NetConnectionID', u'NetConnectionStatus',
                    u'Speed', u'GUID'
                ],
                [
                    u'S5EXVM318 ', u' 38:63:BB:44:D0:26 ',
                    u' HPE Ethernet 1Gb 4-port 331i Adapter #3 ', u' nic3-vl302 ', u' 2 ',
                    u' 1000000000 ', u' {5FBD3455-980D-4AD6-BDEE-79B42B7BBDBC}'
                ],
                [
                    u'S5EXVM318 ', u' 38:63:BB:44:D0:27 ',
                    u' HPE Ethernet 1Gb 4-port 331i Adapter #4 ', u' nic4-vl303 ', u' 2 ',
                    u' 1000000000 ', u' {8A1D9DD0-DF30-46CD-87FC-ACB13A5AB2BA}'
                ],
                [
                    u'S5EXVM318 ', u' 38:63:BB:44:D0:24 ',
                    u' HPE Ethernet 1Gb 4-port 331i Adapter ', u' nic1 ', u' 2 ', u'  ',
                    u' {4DA62AA0-8163-459C-9ACE-95B1E729A7DD}'
                ],
                [
                    u'S5EXVM318 ', u' 38:63:BB:44:D0:25 ',
                    u' HPE Ethernet 1Gb 4-port 331i Adapter ', u' nic2 ', u' 2 ', u'  ',
                    u' {FEF2305A-57FD-4AEC-A817-C082565B6AA7}'
                ],
                [
                    u'S5EXVM318 ', u' 38:63:BB:44:D0:24 ',
                    u' Microsoft Network Adapter Multiplexor Driver ', u' LAN ', u' 2 ',
                    u' 2000000000 ', u' {69DCC9F6-FD98-474C-87F8-DD1023C6117C}'
                ],
            ]),
        )) == [
            Service(
                item='HPE Ethernet 1Gb 4-port 331i Adapter 3',
                parameters={
                    'discovered_oper_status': ['1'],
                    'discovered_speed': 1000000000
                },
            ),
            Service(
                item='HPE Ethernet 1Gb 4-port 331i Adapter 4',
                parameters={
                    'discovered_oper_status': ['1'],
                    'discovered_speed': 1000000000
                },
            ),
            Service(
                item='HPE Ethernet 1Gb 4-port 331i Adapter',
                parameters={
                    'discovered_oper_status': ['1'],
                    'discovered_speed': 1000000000
                },
            ),
            Service(
                item='HPE Ethernet 1Gb 4-port 331i Adapter 2',
                parameters={
                    'discovered_oper_status': ['1'],
                    'discovered_speed': 1000000000
                },
            ),
            Service(
                item='LAN',
                parameters={
                    'aggregate': {
                        'member_appearance': 'descr'
                    },
                    'discovered_oper_status': ['1'],
                    'discovered_speed': 2000000000.0
                },
            ),
        ]


IF_SECTION = [
    [u'1418225545.73', u'510'],
    [
        u'8',
        u'instances:',
        u'Broadcom_ABC123_NetXtreme_123_GigE_[Client1]__138',
        u'Broadcom_ABC456_NetXtreme_456_GigE_[Client2]__137',
        u'isatap.{A1A1A1A1-A1A1-A1A1-A1A1-A1A1A1A1A1A1}',
        u'isatap.{B1B1B1B1-B1B1-B1B1-B1B1-B1B1B1B1B1B1}',
        u'isatap.{C1C1C1C1-C1C1-C1C1-C1C1-C1C1C1C1C1C1}',
        u'isatap.{D1D1D1D1-D1D1-D1D1-D1D1-D1D1D1D1D1D1}',
        u'isatap.{E1E1E1E1-E1E1-E1E1-E1E1-E1E1E1E1E1E1}',
        u'isatap.{F1F1F1F1-F1F1-F1F1-F1F1-F1F1F1F1F1F1}',
    ],
    [u'-122', u'3361621296', u'97386123', u'0', u'0', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'-110', u'3437962', u'13245121', u'0', u'0', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'-244', u'2946102', u'6234996', u'0', u'0', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'-58', u'491860', u'7010125', u'0', u'0', u'0', u'0', u'0', u'0', u'bulk_count'],
    [
        u'10', u'1410065408', u'1410065408', u'100000', u'100000', u'100000', u'100000', u'100000',
        u'100000', u'large_rawcount'
    ],
    [u'-246', u'3188924403', u'3975676452', u'0', u'0', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'14', u'1707835', u'4996570', u'0', u'0', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'16', u'1237965', u'1238278', u'0', u'0', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'18', u'302', u'148', u'0', u'0', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'20', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'22', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'-4', u'172696893', u'416676967', u'0', u'0', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'26', u'484056', u'7001439', u'0', u'0', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'28', u'7804', u'8686', u'0', u'0', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'30', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'32', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'34', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'1086', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'1088', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'1090', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'1092', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'1094', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'large_rawcount'],
]


def test_winperf_if_parse_sections():
    winperf_if.parse_winperf_if(IF_SECTION + [
        [u'Node', u'MACAddress', u'Name', u'NetConnectionID', u'NetConnectionStatus'],
        [u'NODE1', u'', u'WAN Miniport (L2TP)', u'', u''],
        [u'NODE1', u'', u'WAN Miniport (SSTP)', u'', u''],
        [u'NODE1', u'', u'WAN Miniport (IKEv2)', u'', u''],
        [u'NODE1', u'', u'WAN Miniport (PPTP)', u'', u''],
        [u'NODE1', u'', u'WAN Miniport (PPPOE)', u'', u''],
        [u'NODE1', u'', u'WAN Miniport (IP)', u'', u''],
        [u'NODE1', u'', u'WAN Miniport (IPv6)', u'', u''],
        [u'NODE1', u'', u'WAN Miniport (Network Monitor)', u'', u''],
        [u'NODE1', u'', u'Hyper-V Virtual Ethernet Adapter', u'', u''],
        [u'NODE1', u'', u'Microsoft Kernel Debug Network Adapter', u'', u''],
        [u'NODE1', u'', u'RAS Async Adapter', u'', u''],
        [u'NODE1', u'', u'Broadcom NetXtreme Gigabit Ethernet', u'SLOT 3 Port 1', u'4'],
        [u'NODE1', u'', u'Broadcom NetXtreme Gigabit Ethernet', u'SLOT 3 Port 2', u'4'],
        [
            u'NODE1', u'AA:AA:AA:AA:AA:AA',
            u'Broadcom BCM57800 NetXtreme II 10 GigE (NDIS VBD Client)', u'NIC2', u'2'
        ],
        [u'NODE1', u'', u'Broadcom NetXtreme Gigabit Ethernet', u'SLOT 3 Port 4', u'4'],
        [u'NODE1', u'', u'Broadcom NetXtreme Gigabit Ethernet', u'SLOT 3 Port 3', u'4'],
        [u'NODE1', u'', u'Broadcom BCM57800 NetXtreme II 1 GigE (NDIS VBD Client)', u'NIC4', u'4'],
        [u'NODE1', u'', u'Broadcom BCM57800 NetXtreme II 1 GigE (NDIS VBD Client)', u'NIC3', u'4'],
        [
            u'NODE1', u'AA:AA:AA:AA:AA:AA',
            u'Broadcom BCM57800 NetXtreme II 10 GigE (NDIS VBD Client)', u'NIC1', u'2'
        ],
        [u'NODE1', u'', u'Microsoft ISATAP Adapter', u'', u''],
        [u'NODE1', u'', u'Microsoft ISATAP Adapter #2', u'', u''],
        [u'NODE1', u'', u'Microsoft ISATAP Adapter #3', u'', u''],
        [u'NODE1', u'', u'Microsoft ISATAP Adapter #4', u'', u''],
        [u'NODE1', u'', u'Microsoft Network Adapter Multiplexor Default Miniport', u'', u''],
        [
            u'NODE1', u'AA:AA:AA:AA:AA:AA', u'Microsoft Network Adapter Multiplexor Driver',
            u'10GTeam', u'2'
        ],
        [u'NODE1', u'', u'Hyper-V Virtual Switch Extension Adapter', u'', u''],
        [
            u'NODE1', u'AA:AA:AA:AA:AA:AA', u'Hyper-V Virtual Ethernet Adapter #2', u'Management',
            u'2'
        ],
        [u'NODE1', u'AA:AA:AA:AA:AA:AA', u'Hyper-V Virtual Ethernet Adapter #3', u'CSV', u'2'],
        [u'NODE1', u'AA:AA:AA:AA:AA:AA', u'Hyper-V Virtual Ethernet Adapter #4', u'Live', u'2'],
        [u'NODE1', u'AA:AA:AA:AA:AA:AA', u'Hyper-V Virtual Ethernet Adapter #5', u'iSCSI1', u'2'],
        [u'NODE1', u'AA:AA:AA:AA:AA:AA', u'Hyper-V Virtual Ethernet Adapter #6', u'iSCSI2', u'2'],
        [u'NODE1', u'', u'Microsoft ISATAP Adapter #5', u'', u''],
        [u'NODE1', u'AA:AA:AA:AA:AA:AA', u'Microsoft Failover Cluster Virtual Adapter', u'', u''],
        [u'NODE1', u'', u'Microsoft ISATAP Adapter #6', u'', u''],
    ])


def test_winperf_if_group_patterns(value_store):
    expected_services = [
        Service(item='Broadcom ABC123 NetXtreme 123 GigE [Client1] 138',
                parameters={
                    'discovered_oper_status': ['1'],
                    'discovered_speed': 1410065408
                }),
        Service(item='Broadcom ABC456 NetXtreme 456 GigE [Client2] 137',
                parameters={
                    'discovered_oper_status': ['1'],
                    'discovered_speed': 1410065408
                }),
        Service(item='Broadcom',
                parameters={
                    'aggregate': {
                        'member_appearance': 'descr',
                        'inclusion_condition': {
                            'match_desc': [
                                'Broadcom ABC123 NetXtreme 123 GigE \\[Client1\\] 138',
                                'Broadcom ABC456 NetXtreme 456 GigE \\[Client2\\] 137'
                            ]
                        },
                        'exclusion_conditions': []
                    },
                    'discovered_oper_status': ['1'],
                    'discovered_speed': 2820130816.0
                }),
        Service(item='isatap',
                parameters={
                    'aggregate': {
                        'member_appearance': 'descr',
                        'inclusion_condition': {
                            'match_desc': [
                                'isatap.{A1A1A1A1-A1A1-A1A1-A1A1-A1A1A1A1A1A1}',
                                'isatap.{B1B1B1B1-B1B1-B1B1-B1B1-B1B1B1B1B1B1}',
                                'isatap.{C1C1C1C1-C1C1-C1C1-C1C1-C1C1C1C1C1C1}',
                                'isatap.{D1D1D1D1-D1D1-D1D1-D1D1-D1D1D1D1D1D1}',
                                'isatap.{E1E1E1E1-E1E1-E1E1-E1E1-E1E1E1E1E1E1}',
                                'isatap.{F1F1F1F1-F1F1-F1F1-F1F1-F1F1F1F1F1F1}'
                            ]
                        },
                        'exclusion_conditions': []
                    },
                    'discovered_oper_status': ['1'],
                    'discovered_speed': 600000.0
                }),
    ]
    section = winperf_if.parse_winperf_if(IF_SECTION)
    assert list(
        winperf_if.discover_winperf_if(
            [
                type_defs.Parameters({
                    'discovery_single': (
                        False,
                        {},
                    ),
                    'grouping': (
                        True,
                        [
                            {
                                'group_name': 'isatap',
                                'member_appearance': 'descr',
                            },
                        ],
                    ),
                    'matching_conditions': (
                        False,
                        {
                            'match_desc': [
                                'isatap.{A1A1A1A1-A1A1-A1A1-A1A1-A1A1A1A1A1A1}',
                                'isatap.{B1B1B1B1-B1B1-B1B1-B1B1-B1B1B1B1B1B1}',
                                'isatap.{C1C1C1C1-C1C1-C1C1-C1C1-C1C1C1C1C1C1}',
                                'isatap.{D1D1D1D1-D1D1-D1D1-D1D1-D1D1D1D1D1D1}',
                                'isatap.{E1E1E1E1-E1E1-E1E1-E1E1-E1E1E1E1E1E1}',
                                'isatap.{F1F1F1F1-F1F1-F1F1-F1F1-F1F1F1F1F1F1}',
                            ],
                        },
                    ),
                }),
                type_defs.Parameters({
                    'grouping': (
                        True,
                        [
                            {
                                'group_name': 'Broadcom',
                                'member_appearance': 'descr',
                            },
                        ],
                    ),
                    'matching_conditions': (
                        False,
                        {
                            'match_desc': [
                                'Broadcom ABC123 NetXtreme 123 GigE \\[Client1\\] 138',
                                'Broadcom ABC456 NetXtreme 456 GigE \\[Client2\\] 137',
                            ],
                        },
                    ),
                }),
                type_defs.Parameters({
                    **interfaces.DISCOVERY_DEFAULT_PARAMETERS,
                    'discovery_single': (
                        True,
                        {
                            'item_appearance': 'descr',
                            'pad_portnumbers': True,
                        },
                    ),
                }),
            ],
            section,
        )) == expected_services

    assert [
        result for service in expected_services for result in winperf_if.check_winperf_if(
            service.item or "",  # or "" to make mypy happy
            type_defs.Parameters(service.parameters),
            section,
        ) if not isinstance(result, IgnoreResults)
    ] == [
        Result(state=state.OK, summary='[1]', details='[1]'),
        Result(state=state.OK,
               summary='Operational state: Connected',
               details='Operational state: Connected'),
        Result(state=state.OK, summary='1.41 GBit/s', details='1.41 GBit/s'),
        Result(state=state.OK, summary='[2]', details='[2]'),
        Result(state=state.OK,
               summary='Operational state: Connected',
               details='Operational state: Connected'),
        Result(state=state.OK, summary='1.41 GBit/s', details='1.41 GBit/s'),
        Result(state=state.OK, summary='Teaming', details='Teaming'),
        Result(state=state.OK, summary='Operational state: up', details='Operational state: up'),
        Result(
            state=state.OK,
            summary=
            'Members: [Broadcom ABC123 NetXtreme 123 GigE [Client1] 138 (Connected), Broadcom ABC456 NetXtreme 456 GigE [Client2] 137 (Connected)]',
            details=
            'Members: [Broadcom ABC123 NetXtreme 123 GigE [Client1] 138 (Connected), Broadcom ABC456 NetXtreme 456 GigE [Client2] 137 (Connected)]'
        ),
        Result(state=state.OK, summary='2.82 GBit/s', details='2.82 GBit/s'),
        Result(state=state.OK, summary='Teaming', details='Teaming'),
        Result(state=state.OK, summary='Operational state: up', details='Operational state: up'),
        Result(
            state=state.OK,
            summary=
            'Members: [isatap.{A1A1A1A1-A1A1-A1A1-A1A1-A1A1A1A1A1A1} (Connected), isatap.{B1B1B1B1-B1B1-B1B1-B1B1-B1B1B1B1B1B1} (Connected), isatap.{C1C1C1C1-C1C1-C1C1-C1C1-C1C1C1C1C1C1} (Connected), isatap.{D1D1D1D1-D1D1-D1D1-D1D1-D1D1D1D1D1D1} (Connected), isatap.{E1E1E1E1-E1E1-E1E1-E1E1-E1E1E1E1E1E1} (Connected), isatap.{F1F1F1F1-F1F1-F1F1-F1F1-F1F1F1F1F1F1} (Connected)]',
            details=
            'Members: [isatap.{A1A1A1A1-A1A1-A1A1-A1A1-A1A1A1A1A1A1} (Connected), isatap.{B1B1B1B1-B1B1-B1B1-B1B1-B1B1B1B1B1B1} (Connected), isatap.{C1C1C1C1-C1C1-C1C1-C1C1-C1C1C1C1C1C1} (Connected), isatap.{D1D1D1D1-D1D1-D1D1-D1D1-D1D1D1D1D1D1} (Connected), isatap.{E1E1E1E1-E1E1-E1E1-E1E1-E1E1E1E1E1E1} (Connected), isatap.{F1F1F1F1-F1F1-F1F1-F1F1-F1F1F1F1F1F1} (Connected)]'
        ),
        Result(state=state.OK, summary='600 kBit/s', details='600 kBit/s'),
    ]


def winperf_if_teaming_parsed(time, out_octets):
    return (
        time,
        [
            # ((u'DAG-NET', '8'), u'Intel[R] Ethernet 10G 2P X520 Adapter 4', '6', 10000000000,
            #  ('1', 'Connected'), 145209040, 0, 0, 2099072, 0, 0, out_octets, 0, 0, 0, 0, 0, 0,
            #  u'SLOT 4 Port 2 DAG', '\xa06\x9f\xb0\xb3f'),
            # ((u'DAG-NET', '3'), u'Intel[R] Ethernet 10G 2P X520 Adapter 2', '6', 10000000000,
            #  ('1',
            #   'Connected'), 410232131549, 376555354, 0, 225288, 0, 0, 1171662236873 + out_octets,
            #  833538016, 0, 63489, 0, 0, 0, u'SLOT 6 Port 1 DAG', '\xa06\x9f\xb0\xa3`'),
            interfaces.Interface(
                index='3',
                descr='Intel[R] Ethernet 10G 2P X520 Adapter 2',
                alias='SLOT 6 Port 1 DAG',
                type='6',
                speed=10000000000,
                oper_status='1',
                in_octets=410232131549,
                in_ucast=376555354,
                in_bcast=225288,
                out_octets=1171662236873 + out_octets,
                out_ucast=833538016,
                out_bcast=63489,
                phys_address='\xa06\x9f\xb0\xa3`',
                oper_status_name='Connected',
                group='DAG-NET',
            ),
            interfaces.Interface(
                index='8',
                descr='Intel[R] Ethernet 10G 2P X520 Adapter 4',
                alias='SLOT 4 Port 2 DAG',
                type='6',
                speed=10000000000,
                oper_status='1',
                in_octets=145209040,
                in_bcast=2099072,
                out_octets=out_octets,
                phys_address='\xa06\x9f\xb0\xb3f',
                oper_status_name='Connected',
                group='DAG-NET',
            ),
        ],
        {},
    )


@pytest.mark.parametrize("item, params, results", [
    (
        '3',
        {
            'discovered_oper_status': ['1'],
            'discovered_speed': 10000000000
        },
        [
            Result(state=state.OK, summary='[SLOT 6 Port 1 DAG]', details='[SLOT 6 Port 1 DAG]'),
            Result(state=state.OK,
                   summary='Operational state: Connected',
                   details='Operational state: Connected'),
            Result(
                state=state.OK, summary='MAC: A0:36:9F:B0:A3:60', details='MAC: A0:36:9F:B0:A3:60'),
            Result(state=state.OK, summary='10 GBit/s', details='10 GBit/s'),
            Metric('in', 0.0, levels=(None, None), boundaries=(0.0, 1250000000.0)),
            Metric('inmcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('inbcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('inucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('innucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('indisc', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('inerr', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('out', 1073741824.0, levels=(None, None), boundaries=(0.0, 1250000000.0)),
            Metric('outmcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outbcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outnucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outdisc', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outerr', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outqlen', 0.0, levels=(None, None), boundaries=(None, None)),
            Result(state=state.OK, summary='In: 0.00 B/s (0.0%)', details='In: 0.00 B/s (0.0%)'),
            Result(
                state=state.OK, summary='Out: 1.07 GB/s (85.9%)', details='Out: 1.07 GB/s (85.9%)'),
        ],
    ),
    (
        '8',
        {
            'discovered_oper_status': ['1'],
            'discovered_speed': 10000000000
        },
        [
            Result(state=state.OK, summary='[SLOT 4 Port 2 DAG]', details='[SLOT 4 Port 2 DAG]'),
            Result(state=state.OK,
                   summary='Operational state: Connected',
                   details='Operational state: Connected'),
            Result(
                state=state.OK, summary='MAC: A0:36:9F:B0:B3:66', details='MAC: A0:36:9F:B0:B3:66'),
            Result(state=state.OK, summary='10 GBit/s', details='10 GBit/s'),
            Metric('in', 0.0, levels=(None, None), boundaries=(0.0, 1250000000.0)),
            Metric('inmcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('inbcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('inucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('innucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('indisc', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('inerr', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('out', 1073741824.0, levels=(None, None), boundaries=(0.0, 1250000000.0)),
            Metric('outmcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outbcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outnucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outdisc', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outerr', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outqlen', 0.0, levels=(None, None), boundaries=(None, None)),
            Result(state=state.OK, summary='In: 0.00 B/s (0.0%)', details='In: 0.00 B/s (0.0%)'),
            Result(
                state=state.OK, summary='Out: 1.07 GB/s (85.9%)', details='Out: 1.07 GB/s (85.9%)'),
        ],
    ),
    (
        'DAG-NET',
        {
            'discovered_oper_status': ['1'],
            'discovered_speed': 20000000000,
            'aggregate': {
                'member_appearance': 'index',
            },
        },
        [
            Result(state=state.OK, summary='Teaming', details='Teaming'),
            Result(state=state.OK, summary='Operational state: up',
                   details='Operational state: up'),
            Result(state=state.OK,
                   summary='Members: [3 (Connected), 8 (Connected)]',
                   details='Members: [3 (Connected), 8 (Connected)]'),
            Result(state=state.OK, summary='20 GBit/s', details='20 GBit/s'),
            Metric('in', 0.0, levels=(None, None), boundaries=(0.0, 2500000000.0)),
            Metric('inmcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('inbcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('inucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('innucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('indisc', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('inerr', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('out', 2147483648.0, levels=(None, None), boundaries=(0.0, 2500000000.0)),
            Metric('outmcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outbcast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outnucast', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outdisc', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outerr', 0.0, levels=(None, None), boundaries=(None, None)),
            Metric('outqlen', 0.0, levels=(None, None), boundaries=(None, None)),
            Result(state=state.OK, summary='In: 0.00 B/s (0.0%)', details='In: 0.00 B/s (0.0%)'),
            Result(
                state=state.OK, summary='Out: 2.15 GB/s (85.9%)', details='Out: 2.15 GB/s (85.9%)'),
        ],
    ),
])
def test_winperf_if_teaming_performance_data(monkeypatch, value_store, item, params, results):
    # Initialize counters
    monkeypatch.setattr('time.time', lambda: 0)
    with suppress(IgnoreResultsError):
        list(
            winperf_if.check_winperf_if(
                item,
                type_defs.Parameters(params),
                winperf_if_teaming_parsed(0, 0),
            ))

    # winperf_if should use the timestamp of the parsed data. To check that it does not use
    # time.time by accident, we set it to 20 s instead of 10 s. If winperf_if would now used
    # time.time the, the out metric value would be smaller.
    monkeypatch.setattr('time.time', lambda: 20)
    assert list(
        winperf_if.check_winperf_if(
            item,
            type_defs.Parameters(params),
            winperf_if_teaming_parsed(10, 1024 * 1024 * 1024 * 10),
        )) == results


@pytest.mark.parametrize('string_table, discovery_results, items_params_results', [
    (
        [
            [u'1457449582.48', u'510'],
            [u'2', u'instances:', u'TEAM:F[o]O_123-BAR', u'TEAM:F[o]O_123-BAR__2'],
            [u'-122', u'235633280233', u'654530712228', u'bulk_count'],
            [u'-110', u'242545296', u'495547559', u'bulk_count'],
            [u'-244', u'104845218', u'401387884', u'bulk_count'],
            [u'-58', u'137700078', u'94159675', u'bulk_count'],
            [u'10', u'10000000000', u'10000000000', u'large_rawcount'],
            [u'-246', u'102711323759', u'558990881384', u'bulk_count'],
            [u'14', u'104671447', u'400620918', u'bulk_count'],
            [u'16', u'173771', u'766966', u'bulk_count'],
            [u'18', u'0', u'0', u'large_rawcount'],
            [u'20', u'0', u'0', u'large_rawcount'],
            [u'22', u'0', u'0', u'large_rawcount'],
            [u'-4', u'132921956474', u'95539830844', u'bulk_count'],
            [u'26', u'137690798', u'94151631', u'bulk_count'],
            [u'28', u'9280', u'8044', u'bulk_count'],
            [u'30', u'0', u'0', u'large_rawcount'],
            [u'32', u'0', u'0', u'large_rawcount'],
            [u'34', u'0', u'0', u'large_rawcount'],
            [u'1086', u'0', u'0', u'large_rawcount'],
            [u'1088', u'0', u'0', u'large_rawcount'],
            [u'1090', u'0', u'0', u'bulk_count'],
            [u'1092', u'0', u'0', u'bulk_count'],
            [u'1094', u'0', u'0', u'large_rawcount'],
        ],
        [
            Service(
                item='1',
                parameters={
                    'discovered_oper_status': ['1'],
                    'discovered_speed': 10000000000,
                },
            ),
            Service(
                item='2',
                parameters={
                    'discovered_oper_status': ['1'],
                    'discovered_speed': 10000000000,
                },
            ),
        ],
        [
            (
                '1',
                {
                    'errors': (0.01, 0.1),
                    'discovered_speed': 10000000000,
                    'discovered_oper_status': ['1']
                },
                [
                    Result(state=state.OK, summary='[TEAM:F[o]O 123-BAR]'),
                    Result(state=state.OK, summary='Operational state: Connected'),
                    Result(state=state.OK, summary='10 GBit/s'),
                ],
            ),
            (
                '2',
                {
                    'errors': (0.01, 0.1),
                    'discovered_speed': 10000000000,
                    'discovered_oper_status': ['1']
                },
                [
                    Result(state=state.OK, summary='[TEAM:F[o]O 123-BAR 2]'),
                    Result(state=state.OK, summary='Operational state: Connected'),
                    Result(state=state.OK, summary='10 GBit/s'),
                ],
            ),
        ],
    ),
    (
        [[u'1476804932.61', u'510', u'2082740'],
         [u'4', u'instances:', u'A_B-C', u'FOO_B-A-R__53', u'A_B-C__3', u'FOO_B-A-R__52'],
         [
             u'-122', u'246301064630', u'2035719049115', u'191138259305', u'1956798911236',
             u'bulk_count'
         ], [u'-110', u'195002974', u'1888010079', u'157579333', u'1767947062', u'bulk_count'],
         [u'-244', u'81582535', u'531894182', u'42736554', u'450993852', u'bulk_count'],
         [u'-58', u'113420439', u'1356115897', u'114842779', u'1316953210', u'bulk_count'],
         [u'10', u'10000000000', u'1000000000', u'10000000000', u'1000000000', u'large_rawcount'],
         [u'-246', u'85146916834', u'295765890709', u'28180136075', u'244690096455', u'bulk_count'],
         [u'14', u'71520104', u'491241747', u'34804873', u'420107059', u'bulk_count'],
         [u'16', u'10062431', u'40652422', u'7931681', u'30886784', u'bulk_count'],
         [u'18', u'0', u'13', u'0', u'9', u'large_rawcount'],
         [u'20', u'0', u'0', u'0', u'0', u'large_rawcount'],
         [u'22', u'0', u'0', u'0', u'0', u'large_rawcount'],
         [
             u'-4', u'161154147796', u'1739953158406', u'162958123230', u'1712108814781',
             u'bulk_count'
         ], [u'26', u'113162286', u'1355871932', u'114440147', u'1316598654', u'bulk_count'],
         [u'28', u'258153', u'243965', u'402632', u'354556', u'bulk_count'],
         [u'30', u'0', u'0', u'0', u'0', u'large_rawcount'],
         [u'32', u'0', u'0', u'0', u'0', u'large_rawcount'],
         [u'34', u'0', u'0', u'0', u'0', u'large_rawcount'],
         [u'1086', u'0', u'0', u'0', u'0', u'large_rawcount'],
         [u'1088', u'0', u'0', u'0', u'0', u'large_rawcount'],
         [u'1090', u'0', u'0', u'0', u'0', u'bulk_count'],
         [u'1092', u'0', u'0', u'0', u'0', u'bulk_count'],
         [u'1094', u'0', u'0', u'0', u'0', u'large_rawcount'], [u'[teaming_start]'],
         [
             u'TeamName', u'TeamingMode', u'LoadBalancingAlgorithm', u'MemberMACAddresses',
             u'MemberNames', u'MemberDescriptions', u'Speed', u'GUID'
         ],
         [
             u'T1Team ', u'Lacp ', u'Dynamic ', u'00:00:00:00:00:00;00:00:00:00:00:01',
             u'Ethernet 3;Ethernet 6', u'HP1 Adapter;HP1 Adapter #3', u'10000000000;10000000000',
             u'{123-ABC-456};{FOO-123-BAR}'
         ],
         [
             u'T2Team ', u'Lacp ', u'Dynamic ', u'00:00:00:00:00:02;00:00:00:00:00:03',
             u'Ethernet 7;Ethernet 5', u'HP2 Adapter #52;HP2 Adapter #53', u'1000000000;1000000000',
             u'{BAR-456-BAZ};{1-A-2-B-3-C}'
         ], [u'[teaming_end]'],
         [
             u'Node', u'MACAddress', u'Name', u'NetConnectionID', u'NetConnectionStatus', u'Speed',
             u'GUID'
         ],
         [u'ABC123 ', u'  ', u' HP2 Adapter ', u' Ethernet ', u' 4 ', u'  ', u' {FOO_XYZ123-BAR}'],
         [u'ABC123 ', u'  ', u' HP2 Adapter ', u' Ethernet 2 ', u' 4 ', u'  ', u' {987-ZYX-654}'],
         [
             u'ABC123 ', u' 00:00:00:00:00:00 ', u' HP1 Adapter ', u' Ethernet 3 ', u' 2 ', u'  ',
             u' {123-ABC-456}'
         ],
         [u'ABC123 ', u'  ', u' HP1 Adapter ', u' Ethernet 4 ', u' 4 ', u'  ', u' {XYZ-FOO-123}'],
         [
             u'ABC123 ', u' 00:00:00:00:00:01 ', u' HP2 Adapter ', u' Ethernet 5 ', u' 2 ', u'  ',
             u' {1-A-2-B-3-C}'
         ],
         [
             u'ABC123 ', u' 00:00:00:00:00:02 ', u' HP1 Adapter ', u' Ethernet 6 ', u' 2 ', u'  ',
             u' {FOO-123-BAR}'
         ],
         [
             u'ABC123 ', u' 00:00:00:00:00:03 ', u' HP2 Adapter ', u' Ethernet 7 ', u' 2 ', u'  ',
             u' {BAR-456-BAZ}'
         ], [u'ABC123 ', u'  ', u' HP1 Adapter ', u' Ethernet 8 ', u' 4 ', u'  ', u' {FOOBAR-123}'],
         [
             u'ABC123 ', u' 00:00:00:00:00:04 ', u' Microsoft Network Adapter Multiplexor Driver ',
             u' T1Team ', u' 2 ', u' 20000000000 ', u' {456-FOOBAR}'
         ],
         [
             u'ABC123 ', u' 00:00:00:00:00:05 ',
             u' Microsoft Network Adapter Multiplexor Driver #2 ', u' T2Team ', u' 2 ',
             u' 2000000000 ', u' {FOO-1-BAR-2-BAZ-3}'
         ]],
        [
            Service(
                item='1',
                parameters={
                    'discovered_oper_status': ['1'],
                    'discovered_speed': 10000000000,
                },
            ),
            Service(
                item='2',
                parameters={
                    'discovered_oper_status': ['1'],
                    'discovered_speed': 1000000000,
                },
            ),
            Service(
                item='3',
                parameters={
                    'discovered_oper_status': ['1'],
                    'discovered_speed': 10000000000,
                },
            ),
            Service(
                item='4',
                parameters={
                    'discovered_oper_status': ['1'],
                    'discovered_speed': 1000000000,
                },
            ),
        ],
        [
            (
                '1',
                {
                    'errors': (0.01, 0.1),
                    'discovered_speed': 10000000000,
                    'discovered_oper_status': ['1']
                },
                [
                    Result(state=state.OK, summary='[A B-C]'),
                    Result(state=state.OK, summary='Operational state: Connected'),
                    Result(state=state.OK, summary='10 GBit/s'),
                ],
            ),
            (
                '2',
                {
                    'errors': (0.01, 0.1),
                    'discovered_speed': 1000000000,
                    'discovered_oper_status': ['1']
                },
                [
                    Result(state=state.OK, summary='[FOO B-A-R 53]'),
                    Result(state=state.OK, summary='Operational state: Connected'),
                    Result(state=state.OK, summary='1 GBit/s'),
                ],
            ),
            (
                '3',
                {
                    'errors': (0.01, 0.1),
                    'discovered_speed': 10000000000,
                    'discovered_oper_status': ['1']
                },
                [
                    Result(state=state.OK, summary='[A B-C 3]'),
                    Result(state=state.OK, summary='Operational state: Connected'),
                    Result(state=state.OK, summary='10 GBit/s'),
                ],
            ),
            (
                '4',
                {
                    'errors': (0.01, 0.1),
                    'discovered_speed': 1000000000,
                    'discovered_oper_status': ['1']
                },
                [
                    Result(state=state.OK, summary='[FOO B-A-R 52]'),
                    Result(state=state.OK, summary='Operational state: Connected'),
                    Result(state=state.OK, summary='1 GBit/s'),
                ],
            ),
        ],
    ),
])
def test_winperf_if_regression(
    monkeypatch,
    string_table,
    discovery_results,
    items_params_results,
):
    section = winperf_if.parse_winperf_if(string_table)
    assert list(
        winperf_if.discover_winperf_if(
            [type_defs.Parameters(interfaces.DISCOVERY_DEFAULT_PARAMETERS)],
            section,
        )) == discovery_results

    monkeypatch.setattr(interfaces, 'get_value_store', lambda: {})
    for item, par, res in items_params_results:
        assert list(winperf_if.check_winperf_if(
            item,
            type_defs.Parameters(par),
            section,
        )) == res
