#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import suppress

import pytest

from cmk.base.plugins.agent_based import winperf_if
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResults,
    IgnoreResultsError,
    Metric,
    Result,
    Service,
)
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state
from cmk.base.plugins.agent_based.utils import interfaces


@pytest.mark.parametrize(
    "string_table, settings, items",
    [
        ([], {}, []),
        ([["1527487554.76", "510"]], {}, []),
        (
            [
                ["123", "456", "789"],
                ["1", "instances:", "A_B-C_1"],
                ["-122", "29370873405", "5887351577", "0", "0", "bulk_count"],
                ["-110", "5692885", "5153077", "0", "0", "bulk_count"],
                ["-244", "5018312", "4921974", "0", "0", "bulk_count"],
                ["-58", "674573", "231103", "0", "0", "bulk_count"],
                ["10", "10000000000", "10000000000", "100000", "100000", "large_rawcount"],
                ["-246", "20569013293", "5685847946", "0", "0", "bulk_count"],
                ["14", "4961765", "4425455", "0", "0", "bulk_count"],
                ["16", "4447", "490897", "0", "0", "bulk_count"],
                ["18", "52100", "5622", "0", "0", "large_rawcount"],
                ["20", "0", "0", "0", "0", "large_rawcount"],
                ["22", "0", "0", "0", "0", "large_rawcount"],
                ["-4", "8801860112", "201503631", "0", "0", "bulk_count"],
                ["26", "673929", "230448", "0", "0", "bulk_count"],
                ["28", "644", "655", "0", "0", "bulk_count"],
                ["30", "0", "0", "0", "0", "large_rawcount"],
                ["32", "0", "0", "0", "0", "large_rawcount"],
                ["34", "0", "0", "0", "0", "large_rawcount"],
                ["1086", "0", "0", "0", "0", "large_rawcount"],
                ["1088", "1", "0", "0", "0", "large_rawcount"],
                ["1090", "3734320", "4166703", "0", "0", "bulk_count"],
                ["1092", "0", "0", "0", "0", "bulk_count"],
                ["1094", "22618", "22618", "22618", "22618", "large_rawcount"],
                [
                    "Node",
                    "MACAddress",
                    "Name",
                    "NetConnectionID",
                    "NetConnectionStatus",
                    "Speed",
                    "GUID",
                ],
                [
                    "NODE1 ",
                    " 00:00:00:00:00:00 ",
                    " A_B-C_1 ",
                    " Ethernet1-XYZ ",
                    " 2 ",
                    " 10000000000 ",
                    " {FOO-123-BAR}",
                ],
            ],
            {
                "discovery_single": (
                    True,
                    {
                        "item_appearance": "alias",
                        "pad_portnumbers": True,
                    },
                ),
            },
            ["Ethernet1-XYZ"],
        ),
        (
            [
                ["1559837585.63", "510", "2929686"],
                ["1", "instances:", "vmxnet3_Ethernet_Adapter"],
                ["-122", "38840302775", "bulk_count"],
                ["-110", "206904763", "bulk_count"],
                ["-244", "173589803", "bulk_count"],
                ["-58", "33314960", "bulk_count"],
                ["10", "10000000000", "large_rawcount"],
                ["-246", "21145988302", "bulk_count"],
                ["14", "36886547", "bulk_count"],
                ["16", "136703256", "bulk_count"],
                ["18", "0", "large_rawcount"],
                ["20", "0", "large_rawcount"],
                ["22", "0", "large_rawcount"],
                ["-4", "17694314473", "bulk_count"],
                ["26", "33127032", "bulk_count"],
                ["28", "187928", "bulk_count"],
                ["30", "0", "large_rawcount"],
                ["32", "0", "large_rawcount"],
                ["34", "0", "large_rawcount"],
                ["1086", "0", "large_rawcount"],
                ["1088", "0", "large_rawcount"],
                ["1090", "0", "bulk_count"],
                ["1092", "0", "bulk_count"],
                ["1094", "0", "large_rawcount"],
            ],
            {},
            ["1"],
        ),
    ],
)
def test_winperf_if_netconnection_id(string_table, settings, items):
    assert [
        service.item
        for service in winperf_if.discover_winperf_if(
            [
                {
                    **interfaces.DISCOVERY_DEFAULT_PARAMETERS,
                    **settings,
                }
            ],
            winperf_if.parse_winperf_if(string_table),
        )
        if isinstance(service, Service)
    ] == items


def test_winperf_if_inventory_teaming():
    assert list(
        winperf_if.discover_winperf_if(
            [
                {
                    **interfaces.DISCOVERY_DEFAULT_PARAMETERS,
                    "discovery_single": (
                        True,
                        {
                            "item_appearance": "descr",
                            "pad_portnumbers": True,
                        },
                    ),
                }
            ],
            winperf_if.parse_winperf_if(
                [
                    ["1542018413.59", "510", "2341040"],
                    [
                        "4",
                        "instances:",
                        "HPE_Ethernet_1Gb_4-port_331i_Adapter__3",
                        "HPE_Ethernet_1Gb_4-port_331i_Adapter__4",
                        "HPE_Ethernet_1Gb_4-port_331i_Adapter",
                        "HPE_Ethernet_1Gb_4-port_331i_Adapter__2",
                    ],
                    [
                        "-122",
                        "201612106",
                        "187232778",
                        "200985680546908",
                        "969308895925",
                        "bulk_count",
                    ],
                    ["-110", "2938459", "2713782", "141023109713", "7143818358", "bulk_count"],
                    ["-244", "2920458", "2695781", "133889346630", "9159143", "bulk_count"],
                    ["-58", "18001", "18001", "7133763083", "7134659215", "bulk_count"],
                    [
                        "10",
                        "1000000000",
                        "1000000000",
                        "1000000000",
                        "1000000000",
                        "large_rawcount",
                    ],
                    [
                        "-246",
                        "189182492",
                        "174803164",
                        "200050287945665",
                        "730174911",
                        "bulk_count",
                    ],
                    ["14", "0", "0", "133879714188", "131929", "bulk_count"],
                    ["16", "2920458", "2695781", "8946694", "9027210", "bulk_count"],
                    ["18", "0", "0", "685748", "4", "large_rawcount"],
                    ["20", "0", "0", "0", "0", "large_rawcount"],
                    ["22", "0", "0", "0", "0", "large_rawcount"],
                    ["-4", "12429614", "12429614", "935392601243", "968578721014", "bulk_count"],
                    ["26", "0", "0", "7133594582", "7134655376", "bulk_count"],
                    ["28", "18001", "18001", "168501", "3839", "bulk_count"],
                    ["30", "0", "0", "0", "0", "large_rawcount"],
                    ["32", "0", "0", "0", "0", "large_rawcount"],
                    ["34", "0", "0", "0", "0", "large_rawcount"],
                    ["1086", "0", "0", "0", "0", "large_rawcount"],
                    ["1088", "0", "0", "0", "0", "large_rawcount"],
                    ["1090", "0", "0", "0", "0", "bulk_count"],
                    ["1092", "0", "0", "0", "0", "bulk_count"],
                    ["1094", "0", "0", "0", "0", "large_rawcount"],
                    ["[teaming_start]"],
                    [
                        "TeamName",
                        "TeamingMode",
                        "LoadBalancingAlgorithm",
                        "MemberMACAddresses",
                        "MemberNames",
                        "MemberDescriptions",
                        "Speed",
                        "GUID",
                    ],
                    [
                        "LAN ",
                        "SwitchIndependent ",
                        "Dynamic ",
                        "38:63:BB:44:D0:24;38:63:BB:44:D0:25",
                        "nic1;nic2",
                        "HPE Ethernet 1Gb 4-port 331i Adapter;HPE Ethernet 1Gb 4-port 331i Adapter #2",
                        "1000000000;1000000000",
                        "{4DA62AA0-8163-459C-9ACE-95B1E729A7DD};{FEF2305A-57FD-4AEC-A817-C082565B6AA7}",
                    ],
                    ["[teaming_end]"],
                    [
                        "Node",
                        "MACAddress",
                        "Name",
                        "NetConnectionID",
                        "NetConnectionStatus",
                        "Speed",
                        "GUID",
                    ],
                    [
                        "S5EXVM318 ",
                        " 38:63:BB:44:D0:26 ",
                        " HPE Ethernet 1Gb 4-port 331i Adapter #3 ",
                        " nic3-vl302 ",
                        " 2 ",
                        " 1000000000 ",
                        " {5FBD3455-980D-4AD6-BDEE-79B42B7BBDBC}",
                    ],
                    [
                        "S5EXVM318 ",
                        " 38:63:BB:44:D0:27 ",
                        " HPE Ethernet 1Gb 4-port 331i Adapter #4 ",
                        " nic4-vl303 ",
                        " 2 ",
                        " 1000000000 ",
                        " {8A1D9DD0-DF30-46CD-87FC-ACB13A5AB2BA}",
                    ],
                    [
                        "S5EXVM318 ",
                        " 38:63:BB:44:D0:24 ",
                        " HPE Ethernet 1Gb 4-port 331i Adapter ",
                        " nic1 ",
                        " 2 ",
                        "  ",
                        " {4DA62AA0-8163-459C-9ACE-95B1E729A7DD}",
                    ],
                    [
                        "S5EXVM318 ",
                        " 38:63:BB:44:D0:25 ",
                        " HPE Ethernet 1Gb 4-port 331i Adapter ",
                        " nic2 ",
                        " 2 ",
                        "  ",
                        " {FEF2305A-57FD-4AEC-A817-C082565B6AA7}",
                    ],
                    [
                        "S5EXVM318 ",
                        " 38:63:BB:44:D0:24 ",
                        " Microsoft Network Adapter Multiplexor Driver ",
                        " LAN ",
                        " 2 ",
                        " 2000000000 ",
                        " {69DCC9F6-FD98-474C-87F8-DD1023C6117C}",
                    ],
                ]
            ),
        )
    ) == [
        Service(
            item="HPE Ethernet 1Gb 4-port 331i Adapter 3",
            parameters={"discovered_oper_status": ["1"], "discovered_speed": 1000000000},
        ),
        Service(
            item="HPE Ethernet 1Gb 4-port 331i Adapter 4",
            parameters={"discovered_oper_status": ["1"], "discovered_speed": 1000000000},
        ),
        Service(
            item="HPE Ethernet 1Gb 4-port 331i Adapter",
            parameters={"discovered_oper_status": ["1"], "discovered_speed": 1000000000},
        ),
        Service(
            item="HPE Ethernet 1Gb 4-port 331i Adapter 2",
            parameters={"discovered_oper_status": ["1"], "discovered_speed": 1000000000},
        ),
        Service(
            item="LAN",
            parameters={
                "aggregate": {"member_appearance": "descr"},
                "discovered_oper_status": ["1"],
                "discovered_speed": 2000000000.0,
            },
        ),
    ]


IF_SECTION = [
    ["1418225545.73", "510"],
    [
        "8",
        "instances:",
        "Broadcom_ABC123_NetXtreme_123_GigE_[Client1]__138",
        "Broadcom_ABC456_NetXtreme_456_GigE_[Client2]__137",
        "isatap.{A1A1A1A1-A1A1-A1A1-A1A1-A1A1A1A1A1A1}",
        "isatap.{B1B1B1B1-B1B1-B1B1-B1B1-B1B1B1B1B1B1}",
        "isatap.{C1C1C1C1-C1C1-C1C1-C1C1-C1C1C1C1C1C1}",
        "isatap.{D1D1D1D1-D1D1-D1D1-D1D1-D1D1D1D1D1D1}",
        "isatap.{E1E1E1E1-E1E1-E1E1-E1E1-E1E1E1E1E1E1}",
        "isatap.{F1F1F1F1-F1F1-F1F1-F1F1-F1F1F1F1F1F1}",
    ],
    ["-122", "3361621296", "97386123", "0", "0", "0", "0", "0", "0", "bulk_count"],
    ["-110", "3437962", "13245121", "0", "0", "0", "0", "0", "0", "bulk_count"],
    ["-244", "2946102", "6234996", "0", "0", "0", "0", "0", "0", "bulk_count"],
    ["-58", "491860", "7010125", "0", "0", "0", "0", "0", "0", "bulk_count"],
    [
        "10",
        "1410065408",
        "1410065408",
        "100000",
        "100000",
        "100000",
        "100000",
        "100000",
        "100000",
        "large_rawcount",
    ],
    ["-246", "3188924403", "3975676452", "0", "0", "0", "0", "0", "0", "bulk_count"],
    ["14", "1707835", "4996570", "0", "0", "0", "0", "0", "0", "bulk_count"],
    ["16", "1237965", "1238278", "0", "0", "0", "0", "0", "0", "bulk_count"],
    ["18", "302", "148", "0", "0", "0", "0", "0", "0", "large_rawcount"],
    ["20", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
    ["22", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
    ["-4", "172696893", "416676967", "0", "0", "0", "0", "0", "0", "bulk_count"],
    ["26", "484056", "7001439", "0", "0", "0", "0", "0", "0", "bulk_count"],
    ["28", "7804", "8686", "0", "0", "0", "0", "0", "0", "bulk_count"],
    ["30", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
    ["32", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
    ["34", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
    ["1086", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
    ["1088", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
    ["1090", "0", "0", "0", "0", "0", "0", "0", "0", "bulk_count"],
    ["1092", "0", "0", "0", "0", "0", "0", "0", "0", "bulk_count"],
    ["1094", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
]


def test_winperf_if_parse_sections():
    winperf_if.parse_winperf_if(
        IF_SECTION
        + [
            ["Node", "MACAddress", "Name", "NetConnectionID", "NetConnectionStatus"],
            ["NODE1", "", "WAN Miniport (L2TP)", "", ""],
            ["NODE1", "", "WAN Miniport (SSTP)", "", ""],
            ["NODE1", "", "WAN Miniport (IKEv2)", "", ""],
            ["NODE1", "", "WAN Miniport (PPTP)", "", ""],
            ["NODE1", "", "WAN Miniport (PPPOE)", "", ""],
            ["NODE1", "", "WAN Miniport (IP)", "", ""],
            ["NODE1", "", "WAN Miniport (IPv6)", "", ""],
            ["NODE1", "", "WAN Miniport (Network Monitor)", "", ""],
            ["NODE1", "", "Hyper-V Virtual Ethernet Adapter", "", ""],
            ["NODE1", "", "Microsoft Kernel Debug Network Adapter", "", ""],
            ["NODE1", "", "RAS Async Adapter", "", ""],
            ["NODE1", "", "Broadcom NetXtreme Gigabit Ethernet", "SLOT 3 Port 1", "4"],
            ["NODE1", "", "Broadcom NetXtreme Gigabit Ethernet", "SLOT 3 Port 2", "4"],
            [
                "NODE1",
                "AA:AA:AA:AA:AA:AA",
                "Broadcom BCM57800 NetXtreme II 10 GigE (NDIS VBD Client)",
                "NIC2",
                "2",
            ],
            ["NODE1", "", "Broadcom NetXtreme Gigabit Ethernet", "SLOT 3 Port 4", "4"],
            ["NODE1", "", "Broadcom NetXtreme Gigabit Ethernet", "SLOT 3 Port 3", "4"],
            ["NODE1", "", "Broadcom BCM57800 NetXtreme II 1 GigE (NDIS VBD Client)", "NIC4", "4"],
            ["NODE1", "", "Broadcom BCM57800 NetXtreme II 1 GigE (NDIS VBD Client)", "NIC3", "4"],
            [
                "NODE1",
                "AA:AA:AA:AA:AA:AA",
                "Broadcom BCM57800 NetXtreme II 10 GigE (NDIS VBD Client)",
                "NIC1",
                "2",
            ],
            ["NODE1", "", "Microsoft ISATAP Adapter", "", ""],
            ["NODE1", "", "Microsoft ISATAP Adapter #2", "", ""],
            ["NODE1", "", "Microsoft ISATAP Adapter #3", "", ""],
            ["NODE1", "", "Microsoft ISATAP Adapter #4", "", ""],
            ["NODE1", "", "Microsoft Network Adapter Multiplexor Default Miniport", "", ""],
            [
                "NODE1",
                "AA:AA:AA:AA:AA:AA",
                "Microsoft Network Adapter Multiplexor Driver",
                "10GTeam",
                "2",
            ],
            ["NODE1", "", "Hyper-V Virtual Switch Extension Adapter", "", ""],
            [
                "NODE1",
                "AA:AA:AA:AA:AA:AA",
                "Hyper-V Virtual Ethernet Adapter #2",
                "Management",
                "2",
            ],
            ["NODE1", "AA:AA:AA:AA:AA:AA", "Hyper-V Virtual Ethernet Adapter #3", "CSV", "2"],
            ["NODE1", "AA:AA:AA:AA:AA:AA", "Hyper-V Virtual Ethernet Adapter #4", "Live", "2"],
            ["NODE1", "AA:AA:AA:AA:AA:AA", "Hyper-V Virtual Ethernet Adapter #5", "iSCSI1", "2"],
            ["NODE1", "AA:AA:AA:AA:AA:AA", "Hyper-V Virtual Ethernet Adapter #6", "iSCSI2", "2"],
            ["NODE1", "", "Microsoft ISATAP Adapter #5", "", ""],
            ["NODE1", "AA:AA:AA:AA:AA:AA", "Microsoft Failover Cluster Virtual Adapter", "", ""],
            ["NODE1", "", "Microsoft ISATAP Adapter #6", "", ""],
        ]
    )


def test_winperf_if_group_patterns():
    expected_services = [
        Service(
            item="Broadcom ABC123 NetXtreme 123 GigE [Client1] 138",
            parameters={"discovered_oper_status": ["1"], "discovered_speed": 1410065408},
        ),
        Service(
            item="Broadcom ABC456 NetXtreme 456 GigE [Client2] 137",
            parameters={"discovered_oper_status": ["1"], "discovered_speed": 1410065408},
        ),
        Service(
            item="Broadcom",
            parameters={
                "aggregate": {
                    "member_appearance": "descr",
                    "inclusion_condition": {
                        "match_desc": [
                            "Broadcom ABC123 NetXtreme 123 GigE \\[Client1\\] 138",
                            "Broadcom ABC456 NetXtreme 456 GigE \\[Client2\\] 137",
                        ]
                    },
                    "exclusion_conditions": [],
                },
                "discovered_oper_status": ["1"],
                "discovered_speed": 2820130816.0,
            },
        ),
        Service(
            item="isatap",
            parameters={
                "aggregate": {
                    "member_appearance": "descr",
                    "inclusion_condition": {
                        "match_desc": [
                            "isatap.{A1A1A1A1-A1A1-A1A1-A1A1-A1A1A1A1A1A1}",
                            "isatap.{B1B1B1B1-B1B1-B1B1-B1B1-B1B1B1B1B1B1}",
                            "isatap.{C1C1C1C1-C1C1-C1C1-C1C1-C1C1C1C1C1C1}",
                            "isatap.{D1D1D1D1-D1D1-D1D1-D1D1-D1D1D1D1D1D1}",
                            "isatap.{E1E1E1E1-E1E1-E1E1-E1E1-E1E1E1E1E1E1}",
                            "isatap.{F1F1F1F1-F1F1-F1F1-F1F1-F1F1F1F1F1F1}",
                        ]
                    },
                    "exclusion_conditions": [],
                },
                "discovered_oper_status": ["1"],
                "discovered_speed": 600000.0,
            },
        ),
    ]
    section = winperf_if.parse_winperf_if(IF_SECTION)
    assert (
        list(
            winperf_if.discover_winperf_if(
                [
                    {
                        "discovery_single": (
                            False,
                            {},
                        ),
                        "grouping": (
                            True,
                            {
                                "group_items": [
                                    {
                                        "group_name": "isatap",
                                        "member_appearance": "descr",
                                    },
                                ],
                            },
                        ),
                        "matching_conditions": (
                            False,
                            {
                                "match_desc": [
                                    "isatap.{A1A1A1A1-A1A1-A1A1-A1A1-A1A1A1A1A1A1}",
                                    "isatap.{B1B1B1B1-B1B1-B1B1-B1B1-B1B1B1B1B1B1}",
                                    "isatap.{C1C1C1C1-C1C1-C1C1-C1C1-C1C1C1C1C1C1}",
                                    "isatap.{D1D1D1D1-D1D1-D1D1-D1D1-D1D1D1D1D1D1}",
                                    "isatap.{E1E1E1E1-E1E1-E1E1-E1E1-E1E1E1E1E1E1}",
                                    "isatap.{F1F1F1F1-F1F1-F1F1-F1F1-F1F1F1F1F1F1}",
                                ],
                            },
                        ),
                    },
                    {
                        "grouping": (
                            True,
                            {
                                "group_items": [
                                    {
                                        "group_name": "Broadcom",
                                        "member_appearance": "descr",
                                    },
                                ],
                            },
                        ),
                        "matching_conditions": (
                            False,
                            {
                                "match_desc": [
                                    "Broadcom ABC123 NetXtreme 123 GigE \\[Client1\\] 138",
                                    "Broadcom ABC456 NetXtreme 456 GigE \\[Client2\\] 137",
                                ],
                            },
                        ),
                    },
                    {
                        **interfaces.DISCOVERY_DEFAULT_PARAMETERS,
                        "discovery_single": (
                            True,
                            {
                                "item_appearance": "descr",
                                "pad_portnumbers": True,
                            },
                        ),
                    },
                ],
                section,
            )
        )
        == expected_services
    )

    assert [
        result
        for service in expected_services
        for result in winperf_if.check_winperf_if(
            service.item or "",  # or "" to make mypy happy
            service.parameters,
            section,
        )
        if not isinstance(result, IgnoreResults)
    ] == [
        Result(state=state.OK, summary="[1]"),
        Result(state=state.OK, summary="(Connected)", details="Operational state: Connected"),
        Result(state=state.OK, summary="Speed: 1.41 GBit/s"),
        Result(state=state.OK, summary="[2]"),
        Result(state=state.OK, summary="(Connected)", details="Operational state: Connected"),
        Result(state=state.OK, summary="Speed: 1.41 GBit/s"),
        Result(state=state.OK, summary="Teaming"),
        Result(state=state.OK, summary="(up)", details="Operational state: up"),
        Result(
            state=state.OK,
            summary=(
                "Members: [Broadcom ABC123 NetXtreme 123 GigE [Client1] 138 (Connected),"
                " Broadcom ABC456 NetXtreme 456 GigE [Client2] 137 (Connected)]"
            ),
        ),
        Result(state=state.OK, summary="Speed: 2.82 GBit/s"),
        Result(state=state.OK, summary="Teaming"),
        Result(state=state.OK, summary="(up)", details="Operational state: up"),
        Result(
            state=state.OK,
            summary=(
                "Members: [isatap.{A1A1A1A1-A1A1-A1A1-A1A1-A1A1A1A1A1A1} (Connected),"
                " isatap.{B1B1B1B1-B1B1-B1B1-B1B1-B1B1B1B1B1B1} (Connected),"
                " isatap.{C1C1C1C1-C1C1-C1C1-C1C1-C1C1C1C1C1C1} (Connected),"
                " isatap.{D1D1D1D1-D1D1-D1D1-D1D1-D1D1D1D1D1D1} (Connected),"
                " isatap.{E1E1E1E1-E1E1-E1E1-E1E1-E1E1E1E1E1E1} (Connected),"
                " isatap.{F1F1F1F1-F1F1-F1F1-F1F1-F1F1F1F1F1F1} (Connected)]"
            ),
        ),
        Result(state=state.OK, summary="Speed: 600 kBit/s"),
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
                index="3",
                descr="Intel[R] Ethernet 10G 2P X520 Adapter 2",
                alias="SLOT 6 Port 1 DAG",
                type="6",
                speed=10000000000,
                oper_status="1",
                in_octets=410232131549,
                in_ucast=376555354,
                in_bcast=225288,
                out_octets=1171662236873 + out_octets,
                out_ucast=833538016,
                out_bcast=63489,
                phys_address="\xa06\x9f\xb0\xa3`",
                oper_status_name="Connected",
                group="DAG-NET",
            ),
            interfaces.Interface(
                index="8",
                descr="Intel[R] Ethernet 10G 2P X520 Adapter 4",
                alias="SLOT 4 Port 2 DAG",
                type="6",
                speed=10000000000,
                oper_status="1",
                in_octets=145209040,
                in_bcast=2099072,
                out_octets=out_octets,
                phys_address="\xa06\x9f\xb0\xb3f",
                oper_status_name="Connected",
                group="DAG-NET",
            ),
        ],
        {},
    )


@pytest.mark.parametrize(
    "item, params, results",
    [
        (
            "3",
            {"discovered_oper_status": ["1"], "discovered_speed": 10000000000},
            [
                Result(state=state.OK, summary="[SLOT 6 Port 1 DAG]"),
                Result(
                    state=state.OK, summary="(Connected)", details="Operational state: Connected"
                ),
                Result(state=state.OK, summary="MAC: A0:36:9F:B0:A3:60"),
                Result(state=state.OK, summary="Speed: 10 GBit/s"),
                Metric("outqlen", 0.0),
                Result(state=state.OK, summary="In: 0.00 B/s (0%)"),
                Metric("in", 0.0, boundaries=(0.0, 1250000000.0)),
                Result(state=state.OK, summary="Out: 1.07 GB/s (85.90%)"),
                Metric("out", 1073741824.0, boundaries=(0.0, 1250000000.0)),
                Result(state=state.OK, notice="Errors in: 0 packets/s"),
                Metric("inerr", 0.0),
                Result(state=state.OK, notice="Multicast in: 0 packets/s"),
                Metric("inmcast", 0.0),
                Result(state=state.OK, notice="Broadcast in: 0 packets/s"),
                Metric("inbcast", 0.0),
                Result(state=state.OK, notice="Unicast in: 0 packets/s"),
                Metric("inucast", 0.0),
                Result(state=state.OK, notice="Non-unicast in: 0 packets/s"),
                Metric("innucast", 0.0),
                Result(state=state.OK, notice="Discards in: 0 packets/s"),
                Metric("indisc", 0.0),
                Result(state=state.OK, notice="Errors out: 0 packets/s"),
                Metric("outerr", 0.0),
                Result(state=state.OK, notice="Multicast out: 0 packets/s"),
                Metric("outmcast", 0.0),
                Result(state=state.OK, notice="Broadcast out: 0 packets/s"),
                Metric("outbcast", 0.0),
                Result(state=state.OK, notice="Unicast out: 0 packets/s"),
                Metric("outucast", 0.0),
                Result(state=state.OK, notice="Non-unicast out: 0 packets/s"),
                Metric("outnucast", 0.0),
                Result(state=state.OK, notice="Discards out: 0 packets/s"),
                Metric("outdisc", 0.0),
            ],
        ),
        (
            "8",
            {"discovered_oper_status": ["1"], "discovered_speed": 10000000000},
            [
                Result(state=state.OK, summary="[SLOT 4 Port 2 DAG]"),
                Result(
                    state=state.OK, summary="(Connected)", details="Operational state: Connected"
                ),
                Result(state=state.OK, summary="MAC: A0:36:9F:B0:B3:66"),
                Result(state=state.OK, summary="Speed: 10 GBit/s"),
                Metric("outqlen", 0.0),
                Result(state=state.OK, summary="In: 0.00 B/s (0%)"),
                Metric("in", 0.0, boundaries=(0.0, 1250000000.0)),
                Result(state=state.OK, summary="Out: 1.07 GB/s (85.90%)"),
                Metric("out", 1073741824.0, boundaries=(0.0, 1250000000.0)),
                Result(state=state.OK, notice="Errors in: 0 packets/s"),
                Metric("inerr", 0.0),
                Result(state=state.OK, notice="Multicast in: 0 packets/s"),
                Metric("inmcast", 0.0),
                Result(state=state.OK, notice="Broadcast in: 0 packets/s"),
                Metric("inbcast", 0.0),
                Result(state=state.OK, notice="Unicast in: 0 packets/s"),
                Metric("inucast", 0.0),
                Result(state=state.OK, notice="Non-unicast in: 0 packets/s"),
                Metric("innucast", 0.0),
                Result(state=state.OK, notice="Discards in: 0 packets/s"),
                Metric("indisc", 0.0),
                Result(state=state.OK, notice="Errors out: 0 packets/s"),
                Metric("outerr", 0.0),
                Result(state=state.OK, notice="Multicast out: 0 packets/s"),
                Metric("outmcast", 0.0),
                Result(state=state.OK, notice="Broadcast out: 0 packets/s"),
                Metric("outbcast", 0.0),
                Result(state=state.OK, notice="Unicast out: 0 packets/s"),
                Metric("outucast", 0.0),
                Result(state=state.OK, notice="Non-unicast out: 0 packets/s"),
                Metric("outnucast", 0.0),
                Result(state=state.OK, notice="Discards out: 0 packets/s"),
                Metric("outdisc", 0.0),
            ],
        ),
        (
            "DAG-NET",
            {
                "discovered_oper_status": ["1"],
                "discovered_speed": 20000000000,
                "aggregate": {
                    "member_appearance": "index",
                },
            },
            [
                Result(state=state.OK, summary="Teaming"),
                Result(state=state.OK, summary="(up)", details="Operational state: up"),
                Result(state=state.OK, summary="Members: [3 (Connected), 8 (Connected)]"),
                Result(state=state.OK, summary="Speed: 20 GBit/s"),
                Metric("outqlen", 0.0),
                Result(state=state.OK, summary="In: 0.00 B/s (0%)"),
                Metric("in", 0.0, boundaries=(0.0, 2500000000.0)),
                Result(state=state.OK, summary="Out: 2.15 GB/s (85.90%)"),
                Metric("out", 2147483648.0, boundaries=(0.0, 2500000000.0)),
                Result(state=state.OK, notice="Errors in: 0 packets/s"),
                Metric("inerr", 0.0),
                Result(state=state.OK, notice="Multicast in: 0 packets/s"),
                Metric("inmcast", 0.0),
                Result(state=state.OK, notice="Broadcast in: 0 packets/s"),
                Metric("inbcast", 0.0),
                Result(state=state.OK, notice="Unicast in: 0 packets/s"),
                Metric("inucast", 0.0),
                Result(state=state.OK, notice="Non-unicast in: 0 packets/s"),
                Metric("innucast", 0.0),
                Result(state=state.OK, notice="Discards in: 0 packets/s"),
                Metric("indisc", 0.0),
                Result(state=state.OK, notice="Errors out: 0 packets/s"),
                Metric("outerr", 0.0),
                Result(state=state.OK, notice="Multicast out: 0 packets/s"),
                Metric("outmcast", 0.0),
                Result(state=state.OK, notice="Broadcast out: 0 packets/s"),
                Metric("outbcast", 0.0),
                Result(state=state.OK, notice="Unicast out: 0 packets/s"),
                Metric("outucast", 0.0),
                Result(state=state.OK, notice="Non-unicast out: 0 packets/s"),
                Metric("outnucast", 0.0),
                Result(state=state.OK, notice="Discards out: 0 packets/s"),
                Metric("outdisc", 0.0),
            ],
        ),
    ],
)
def test_winperf_if_teaming_performance_data(monkeypatch, item, params, results):
    # Initialize counters
    monkeypatch.setattr("time.time", lambda: 0)
    with suppress(IgnoreResultsError):
        list(
            winperf_if.check_winperf_if(
                item,
                params,
                winperf_if_teaming_parsed(0, 0),
            )
        )

    # winperf_if should use the timestamp of the parsed data. To check that it does not use
    # time.time by accident, we set it to 20 s instead of 10 s. If winperf_if would now used
    # time.time the, the out metric value would be smaller.
    monkeypatch.setattr("time.time", lambda: 20)
    assert (
        list(
            winperf_if.check_winperf_if(
                item,
                params,
                winperf_if_teaming_parsed(10, 1024 * 1024 * 1024 * 10),
            )
        )
        == results
    )


@pytest.mark.parametrize(
    "string_table, discovery_results, items_params_results",
    [
        (
            [
                ["1457449582.48", "510"],
                ["2", "instances:", "TEAM:F[o]O_123-BAR", "TEAM:F[o]O_123-BAR__2"],
                ["-122", "235633280233", "654530712228", "bulk_count"],
                ["-110", "242545296", "495547559", "bulk_count"],
                ["-244", "104845218", "401387884", "bulk_count"],
                ["-58", "137700078", "94159675", "bulk_count"],
                ["10", "10000000000", "10000000000", "large_rawcount"],
                ["-246", "102711323759", "558990881384", "bulk_count"],
                ["14", "104671447", "400620918", "bulk_count"],
                ["16", "173771", "766966", "bulk_count"],
                ["18", "0", "0", "large_rawcount"],
                ["20", "0", "0", "large_rawcount"],
                ["22", "0", "0", "large_rawcount"],
                ["-4", "132921956474", "95539830844", "bulk_count"],
                ["26", "137690798", "94151631", "bulk_count"],
                ["28", "9280", "8044", "bulk_count"],
                ["30", "0", "0", "large_rawcount"],
                ["32", "0", "0", "large_rawcount"],
                ["34", "0", "0", "large_rawcount"],
                ["1086", "0", "0", "large_rawcount"],
                ["1088", "0", "0", "large_rawcount"],
                ["1090", "0", "0", "bulk_count"],
                ["1092", "0", "0", "bulk_count"],
                ["1094", "0", "0", "large_rawcount"],
            ],
            [
                Service(
                    item="1",
                    parameters={
                        "discovered_oper_status": ["1"],
                        "discovered_speed": 10000000000,
                    },
                ),
                Service(
                    item="2",
                    parameters={
                        "discovered_oper_status": ["1"],
                        "discovered_speed": 10000000000,
                    },
                ),
            ],
            [
                (
                    "1",
                    {
                        "errors": {"both": ("abs", (10, 20))},
                        "discovered_speed": 10000000000,
                        "discovered_oper_status": ["1"],
                    },
                    [
                        Result(state=state.OK, summary="[TEAM:F[o]O 123-BAR]"),
                        Result(
                            state=state.OK,
                            summary="(Connected)",
                            details="Operational state: Connected",
                        ),
                        Result(state=state.OK, summary="Speed: 10 GBit/s"),
                    ],
                ),
                (
                    "2",
                    {
                        "errors": {"both": ("abs", (10, 20))},
                        "discovered_speed": 10000000000,
                        "discovered_oper_status": ["1"],
                    },
                    [
                        Result(state=state.OK, summary="[TEAM:F[o]O 123-BAR 2]"),
                        Result(
                            state=state.OK,
                            summary="(Connected)",
                            details="Operational state: Connected",
                        ),
                        Result(state=state.OK, summary="Speed: 10 GBit/s"),
                    ],
                ),
            ],
        ),
        (
            [
                ["1476804932.61", "510", "2082740"],
                ["4", "instances:", "A_B-C", "FOO_B-A-R__53", "A_B-C__3", "FOO_B-A-R__52"],
                [
                    "-122",
                    "246301064630",
                    "2035719049115",
                    "191138259305",
                    "1956798911236",
                    "bulk_count",
                ],
                ["-110", "195002974", "1888010079", "157579333", "1767947062", "bulk_count"],
                ["-244", "81582535", "531894182", "42736554", "450993852", "bulk_count"],
                ["-58", "113420439", "1356115897", "114842779", "1316953210", "bulk_count"],
                ["10", "10000000000", "1000000000", "10000000000", "1000000000", "large_rawcount"],
                [
                    "-246",
                    "85146916834",
                    "295765890709",
                    "28180136075",
                    "244690096455",
                    "bulk_count",
                ],
                ["14", "71520104", "491241747", "34804873", "420107059", "bulk_count"],
                ["16", "10062431", "40652422", "7931681", "30886784", "bulk_count"],
                ["18", "0", "13", "0", "9", "large_rawcount"],
                ["20", "0", "0", "0", "0", "large_rawcount"],
                ["22", "0", "0", "0", "0", "large_rawcount"],
                [
                    "-4",
                    "161154147796",
                    "1739953158406",
                    "162958123230",
                    "1712108814781",
                    "bulk_count",
                ],
                ["26", "113162286", "1355871932", "114440147", "1316598654", "bulk_count"],
                ["28", "258153", "243965", "402632", "354556", "bulk_count"],
                ["30", "0", "0", "0", "0", "large_rawcount"],
                ["32", "0", "0", "0", "0", "large_rawcount"],
                ["34", "0", "0", "0", "0", "large_rawcount"],
                ["1086", "0", "0", "0", "0", "large_rawcount"],
                ["1088", "0", "0", "0", "0", "large_rawcount"],
                ["1090", "0", "0", "0", "0", "bulk_count"],
                ["1092", "0", "0", "0", "0", "bulk_count"],
                ["1094", "0", "0", "0", "0", "large_rawcount"],
                ["[teaming_start]"],
                [
                    "TeamName",
                    "TeamingMode",
                    "LoadBalancingAlgorithm",
                    "MemberMACAddresses",
                    "MemberNames",
                    "MemberDescriptions",
                    "Speed",
                    "GUID",
                ],
                [
                    "T1Team ",
                    "Lacp ",
                    "Dynamic ",
                    "00:00:00:00:00:00;00:00:00:00:00:01",
                    "Ethernet 3;Ethernet 6",
                    "HP1 Adapter;HP1 Adapter #3",
                    "10000000000;10000000000",
                    "{123-ABC-456};{FOO-123-BAR}",
                ],
                [
                    "T2Team ",
                    "Lacp ",
                    "Dynamic ",
                    "00:00:00:00:00:02;00:00:00:00:00:03",
                    "Ethernet 7;Ethernet 5",
                    "HP2 Adapter #52;HP2 Adapter #53",
                    "1000000000;1000000000",
                    "{BAR-456-BAZ};{1-A-2-B-3-C}",
                ],
                ["[teaming_end]"],
                [
                    "Node",
                    "MACAddress",
                    "Name",
                    "NetConnectionID",
                    "NetConnectionStatus",
                    "Speed",
                    "GUID",
                ],
                ["ABC123 ", "  ", " HP2 Adapter ", " Ethernet ", " 4 ", "  ", " {FOO_XYZ123-BAR}"],
                ["ABC123 ", "  ", " HP2 Adapter ", " Ethernet 2 ", " 4 ", "  ", " {987-ZYX-654}"],
                [
                    "ABC123 ",
                    " 00:00:00:00:00:00 ",
                    " HP1 Adapter ",
                    " Ethernet 3 ",
                    " 2 ",
                    "  ",
                    " {123-ABC-456}",
                ],
                ["ABC123 ", "  ", " HP1 Adapter ", " Ethernet 4 ", " 4 ", "  ", " {XYZ-FOO-123}"],
                [
                    "ABC123 ",
                    " 00:00:00:00:00:01 ",
                    " HP2 Adapter ",
                    " Ethernet 5 ",
                    " 2 ",
                    "  ",
                    " {1-A-2-B-3-C}",
                ],
                [
                    "ABC123 ",
                    " 00:00:00:00:00:02 ",
                    " HP1 Adapter ",
                    " Ethernet 6 ",
                    " 2 ",
                    "  ",
                    " {FOO-123-BAR}",
                ],
                [
                    "ABC123 ",
                    " 00:00:00:00:00:03 ",
                    " HP2 Adapter ",
                    " Ethernet 7 ",
                    " 2 ",
                    "  ",
                    " {BAR-456-BAZ}",
                ],
                ["ABC123 ", "  ", " HP1 Adapter ", " Ethernet 8 ", " 4 ", "  ", " {FOOBAR-123}"],
                [
                    "ABC123 ",
                    " 00:00:00:00:00:04 ",
                    " Microsoft Network Adapter Multiplexor Driver ",
                    " T1Team ",
                    " 2 ",
                    " 20000000000 ",
                    " {456-FOOBAR}",
                ],
                [
                    "ABC123 ",
                    " 00:00:00:00:00:05 ",
                    " Microsoft Network Adapter Multiplexor Driver #2 ",
                    " T2Team ",
                    " 2 ",
                    " 2000000000 ",
                    " {FOO-1-BAR-2-BAZ-3}",
                ],
            ],
            [
                Service(
                    item="1",
                    parameters={
                        "discovered_oper_status": ["1"],
                        "discovered_speed": 10000000000,
                    },
                ),
                Service(
                    item="2",
                    parameters={
                        "discovered_oper_status": ["1"],
                        "discovered_speed": 1000000000,
                    },
                ),
                Service(
                    item="3",
                    parameters={
                        "discovered_oper_status": ["1"],
                        "discovered_speed": 10000000000,
                    },
                ),
                Service(
                    item="4",
                    parameters={
                        "discovered_oper_status": ["1"],
                        "discovered_speed": 1000000000,
                    },
                ),
            ],
            [
                (
                    "1",
                    {
                        "errors": {"both": ("abs", (10, 20))},
                        "discovered_speed": 10000000000,
                        "discovered_oper_status": ["1"],
                    },
                    [
                        Result(state=state.OK, summary="[A B-C]"),
                        Result(
                            state=state.OK,
                            summary="(Connected)",
                            details="Operational state: Connected",
                        ),
                        Result(state=state.OK, summary="Speed: 10 GBit/s"),
                    ],
                ),
                (
                    "2",
                    {
                        "errors": {"both": ("abs", (10, 20))},
                        "discovered_speed": 1000000000,
                        "discovered_oper_status": ["1"],
                    },
                    [
                        Result(state=state.OK, summary="[FOO B-A-R 53]"),
                        Result(
                            state=state.OK,
                            summary="(Connected)",
                            details="Operational state: Connected",
                        ),
                        Result(state=state.OK, summary="Speed: 1 GBit/s"),
                    ],
                ),
                (
                    "3",
                    {
                        "errors": {"both": ("abs", (10, 20))},
                        "discovered_speed": 10000000000,
                        "discovered_oper_status": ["1"],
                    },
                    [
                        Result(state=state.OK, summary="[A B-C 3]"),
                        Result(
                            state=state.OK,
                            summary="(Connected)",
                            details="Operational state: Connected",
                        ),
                        Result(state=state.OK, summary="Speed: 10 GBit/s"),
                    ],
                ),
                (
                    "4",
                    {
                        "errors": {"both": ("abs", (10, 20))},
                        "discovered_speed": 1000000000,
                        "discovered_oper_status": ["1"],
                    },
                    [
                        Result(state=state.OK, summary="[FOO B-A-R 52]"),
                        Result(
                            state=state.OK,
                            summary="(Connected)",
                            details="Operational state: Connected",
                        ),
                        Result(state=state.OK, summary="Speed: 1 GBit/s"),
                    ],
                ),
            ],
        ),
    ],
)
def test_winperf_if_regression(
    monkeypatch,
    string_table,
    discovery_results,
    items_params_results,
):
    section = winperf_if.parse_winperf_if(string_table)
    assert (
        list(
            winperf_if.discover_winperf_if(
                [interfaces.DISCOVERY_DEFAULT_PARAMETERS],
                section,
            )
        )
        == discovery_results
    )

    monkeypatch.setattr(interfaces, "get_value_store", lambda: {})
    for item, par, res in items_params_results:
        assert (
            list(
                winperf_if.check_winperf_if(
                    item,
                    par,
                    section,
                )
            )
            == res
        )
