#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Final

import pytest

from cmk.agent_based.v2 import Attributes, Result, State, StringTable, TableRow
from cmk.plugins.lib import interfaces
from cmk.plugins.windows.agent_based.winperf_if import (
    _check_dhcp,
    _merge_sections,
    AdditionalIfData,
    inventory_winperf_if,
    parse_winperf_if,
    parse_winperf_if_dhcp,
    parse_winperf_if_get_netadapter,
    parse_winperf_if_teaming,
    parse_winperf_if_win32_networkadapter,
    SectionCounters,
    SectionExtended,
    SectionTeaming,
    TeamingData,
)


class Names(StrEnum):
    IBM_USB_2 = "IBM USB Remote NDIS Network Device 2"
    INTEL_I350 = "Intel[R] I350 Gigabit Network Connection"
    INTEL_I350_2 = "Intel[R] I350 Gigabit Network Connection 2"
    INTEL_I350_3 = "Intel[R] I350 Gigabit Network Connection 3"
    INTEL_I350_4 = "Intel[R] I350 Gigabit Network Connection 4"
    INTEL_PRO = "Intel[R] PRO 1000 MT Desktop Adapter"
    QLOGIC = "QLogic 1 10GbE Server Adapter"
    QLOGIC_2 = "QLogic 1 10GbE Server Adapter 2"
    INTEL_NDC = "Intel[R] Gigabit 4P I350-t rNDC"
    INTEL_NDC_2 = "Intel[R] Gigabit 4P I350-t rNDC 2"
    INTEL_NDC_3 = "Intel[R] Gigabit 4P I350-t rNDC 3"
    INTEL_NDC_4 = "Intel[R] Gigabit 4P I350-t rNDC 4"
    INTEL_X520 = "Intel[R] Ethernet 10G 2P X520 Adapter"
    INTEL_X520_2 = "Intel[R] Ethernet 10G 2P X520 Adapter 2"
    INTEL_X520_3 = "Intel[R] Ethernet 10G 2P X520 Adapter 3"
    INTEL_X520_4 = "Intel[R] Ethernet 10G 2P X520 Adapter 4"
    ISATAP_24 = "isatap.{24AA204E-C3FE-47E8-A890-3C1D7584FAF6}"
    ISATAP_2E = "isatap.{2EBF040F-4EA6-4F38-B743-1B4A7BC02F30}"
    ISATAP_A0 = "isatap.{A00F44A5-844B-4679-B2BA-0161B98AE717}"
    ISATAP_09 = "isatap.{09804D64-9D95-4FBF-A8B1-5BE56205FBD8}"
    ISATAP_BF = "isatap.{BF9E1970-5245-46E2-8CA3-87BDF4A9ECAF}"
    ISA = "isatap.rhtz.com"


_counters: Final[dict[Names, interfaces.Counters]] = {
    Names.INTEL_PRO: interfaces.Counters(
        in_octets=60023498,
        in_ucast=42348,
        in_nucast=685,
        in_disc=0,
        in_err=0,
        out_octets=1363362,
        out_ucast=5771,
        out_nucast=126,
        out_disc=0,
        out_err=0,
    ),
    Names.IBM_USB_2: interfaces.Counters(
        in_octets=293841578,
        in_ucast=3089007,
        in_nucast=9289,
        in_disc=0,
        in_err=0,
        out_octets=329096662,
        out_ucast=3089008,
        out_nucast=600757,
        out_disc=0,
        out_err=0,
    ),
    Names.QLOGIC_2: interfaces.Counters(
        in_octets=6273480850,
        in_ucast=5756369,
        in_nucast=592918,
        in_disc=0,
        in_err=0,
        out_octets=2628728624,
        out_ucast=4625712,
        out_nucast=14776,
        out_disc=0,
        out_err=0,
    ),
    Names.QLOGIC: interfaces.Counters(
        in_octets=20846807,
        in_ucast=18266,
        in_nucast=836,
        in_disc=0,
        in_err=0,
        out_octets=3088856,
        out_ucast=8741,
        out_nucast=106,
        out_disc=0,
        out_err=0,
    ),
    Names.INTEL_NDC: interfaces.Counters(
        in_octets=168300731,
        in_ucast=5438,
        in_nucast=2340274,
        in_disc=0,
        in_err=0,
        out_octets=8385014,
        out_ucast=3614,
        out_nucast=65262,
        out_disc=0,
        out_err=0,
    ),
    Names.INTEL_X520: interfaces.Counters(
        in_octets=2568258242370,
        in_ucast=3012412853,
        in_nucast=7601145,
        in_disc=1566,
        in_err=0,
        out_octets=2787714307906,
        out_ucast=2922261424,
        out_nucast=442474,
        out_disc=0,
        out_err=0,
    ),
    Names.INTEL_X520_2: interfaces.Counters(
        in_octets=410232131549,
        in_ucast=376555354,
        in_nucast=225288,
        in_disc=0,
        in_err=0,
        out_octets=1171662236873,
        out_ucast=833538016,
        out_nucast=63489,
        out_disc=0,
        out_err=0,
    ),
    Names.INTEL_X520_3: interfaces.Counters(
        in_octets=271891678,
        in_ucast=0,
        in_nucast=3033012,
        in_disc=0,
        in_err=0,
        out_octets=0,
        out_ucast=0,
        out_nucast=0,
        out_disc=0,
        out_err=0,
    ),
    Names.INTEL_X520_4: interfaces.Counters(
        in_octets=145209040,
        in_ucast=0,
        in_nucast=2099072,
        in_disc=0,
        in_err=0,
        out_octets=0,
        out_ucast=0,
        out_nucast=0,
        out_disc=0,
        out_err=0,
    ),
}


null_counters = interfaces.Counters(
    in_octets=0,
    in_ucast=0,
    in_nucast=0,
    in_disc=0,
    in_err=0,
    out_octets=0,
    out_ucast=0,
    out_nucast=0,
    out_disc=0,
    out_err=0,
)


class Mode(StrEnum):
    UP = "up"
    DISCONN = "Media disconnected"
    DOWN = "down"


def _to_oper_status(mode: Mode) -> int:
    mode_to_int: dict[Mode, int] = {
        Mode.UP: 1,
        Mode.DISCONN: 7,
        Mode.DOWN: 2,
    }
    return mode_to_int[mode]


def _if_attributes(
    index: int,
    name: str,
    speed: int,
    mode: Mode = Mode.UP,
    *,
    alias: str | None = None,
    phys_address: str | None = None,
) -> interfaces.Attributes:
    return interfaces.Attributes(
        index=str(index),
        descr=name,
        alias=name if alias is None else alias,
        type="6",
        speed=speed,
        oper_status=str(_to_oper_status(mode)),
        out_qlen=0,
        phys_address="" if phys_address is None else phys_address,
        oper_status_name=str(mode),
        speed_as_text="",
        group=None,
        node=None,
        admin_status=None,
    )


_Row = Sequence[str]
_Block = Sequence[_Row]

VALID_ONE_IF_INPUT: _Block = [
    ["1630928323.48", "510", "10000000"],
    ["1", "instances:", "Intel[R]_PRO_1000_MT_Desktop_Adapter"],
    ["-122", "61386860", "bulk_count"],
    ["-110", "48930", "bulk_count"],
    ["-244", "43033", "bulk_count"],
    ["-58", "5897", "bulk_count"],
    ["10", "1000000000", "large_rawcount"],
    ["-246", "60023498", "bulk_count"],
    ["14", "42348", "bulk_count"],
    ["16", "685", "bulk_count"],
    ["18", "0", "large_rawcount"],
    ["20", "0", "large_rawcount"],
    ["22", "0", "large_rawcount"],
    ["-4", "1363362", "bulk_count"],
    ["26", "5771", "bulk_count"],
    ["28", "126", "bulk_count"],
    ["30", "0", "large_rawcount"],
    ["32", "0", "large_rawcount"],
    ["34", "0", "large_rawcount"],
    ["1086", "0", "large_rawcount"],
    ["1088", "0", "large_rawcount"],
    ["1090", "0", "bulk_count"],
    ["1092", "0", "bulk_count"],
    ["1094", "0", "large_rawcount"],
]

DHCP_STRANGE_INPUT: _Block = [
    ["[dhcp_start]"],
    ["Description", "DHCPEnabled"],
    ["DOESNT MATTER"],
    ["[dhcp_end]"],
]

MULTIPLY_INTERFACES_INPUT: _Block = [
    ["1425370325.75", "510"],
    [
        "9",
        "instances:",
        "QLogic_1_10GbE_Server_Adapter__2",
        "QLogic_1_10GbE_Server_Adapter",
        "Intel[R]_I350_Gigabit_Network_Connection",
        "Intel[R]_I350_Gigabit_Network_Connection__2",
        "Intel[R]_I350_Gigabit_Network_Connection__3",
        "Intel[R]_I350_Gigabit_Network_Connection__4",
        "IBM_USB_Remote_NDIS_Network_Device__2",
        "isatap.{24AA204E-C3FE-47E8-A890-3C1D7584FAF6}",
        "isatap.{2EBF040F-4EA6-4F38-B743-1B4A7BC02F30}",
    ],
    ["-122", "8902209474", "23935663", "0", "0", "0", "0", "622938240", "0", "0", "bulk_count"],
    ["-110", "10989775", "27949", "0", "0", "0", "0", "6788061", "0", "0", "bulk_count"],
    ["-244", "6349287", "19102", "0", "0", "0", "0", "3098296", "0", "0", "bulk_count"],
    ["-58", "4640488", "8847", "0", "0", "0", "0", "3689765", "0", "0", "bulk_count"],
    [
        "10",
        "10000000000",
        "10000000000",
        "0",
        "0",
        "0",
        "0",
        "9728000",
        "100000",
        "100000",
        "large_rawcount",
    ],
    ["-246", "6273480850", "20846807", "0", "0", "0", "0", "293841578", "0", "0", "bulk_count"],
    ["14", "5756369", "18266", "0", "0", "0", "0", "3089007", "0", "0", "bulk_count"],
    ["16", "592918", "836", "0", "0", "0", "0", "9289", "0", "0", "bulk_count"],
    ["18", "0", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
    ["20", "0", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
    ["22", "0", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
    ["-4", "2628728624", "3088856", "0", "0", "0", "0", "329096662", "0", "0", "bulk_count"],
    ["26", "4625712", "8741", "0", "0", "0", "0", "3089008", "0", "0", "bulk_count"],
    ["28", "14776", "106", "0", "0", "0", "0", "600757", "0", "0", "bulk_count"],
    ["30", "0", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
    ["32", "0", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
    ["34", "0", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
    ["1086", "0", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
    ["1088", "0", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
    ["1090", "0", "0", "0", "0", "0", "0", "0", "0", "0", "bulk_count"],
    ["1092", "0", "0", "0", "0", "0", "0", "0", "0", "0", "bulk_count"],
    ["1094", "0", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
]

MULTIPLY_INTERFACES_12_INPUT: _Block = [
    ["1498114570.10", "5102343752"],
    [
        "12",
        "instances:",
        "Intel[R]_Gigabit_4P_I350-t_rNDC",
        "Intel[R]_Ethernet_10G_2P_X520_Adapter",
        "Intel[R]_Ethernet_10G_2P_X520_Adapter__2",
        "Intel[R]_Gigabit_4P_I350-t_rNDC__2",
        "Intel[R]_Gigabit_4P_I350-t_rNDC__3",
        "Intel[R]_Gigabit_4P_I350-t_rNDC__4",
        "Intel[R]_Ethernet_10G_2P_X520_Adapter__3",
        "Intel[R]_Ethernet_10G_2P_X520_Adapter__4",
        "isatap.rhtz.com",
        "isatap.{A00F44A5-844B-4679-B2BA-0161B98AE717}",
        "isatap.{09804D64-9D95-4FBF-A8B1-5BE56205FBD8}",
        "isatap.{BF9E1970-5245-46E2-8CA3-87BDF4A9ECAF}",
    ],
    [
        "-122",
        "176685745",
        "5355972550276",
        "1581894368422",
        "0",
        "0",
        "0",
        "271891678",
        "145209040",
        "0",
        "0",
        "0",
        "0",
        "bulk_count",
    ],
    [
        "-110",
        "2414588",
        "5942719462",
        "1210382147",
        "0",
        "0",
        "0",
        "3033012",
        "2099072",
        "0",
        "0",
        "0",
        "0",
        "bulk_count",
    ],
    [
        "-244",
        "2345712",
        "3020015564",
        "376780642",
        "0",
        "0",
        "0",
        "3033012",
        "2099072",
        "0",
        "0",
        "0",
        "0",
        "bulk_count",
    ],
    [
        "-58",
        "68876",
        "2922703898",
        "833601505",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "bulk_count",
    ],
    [
        "10",
        "1000000000",
        "10000000000",
        "10000000000",
        "0",
        "0",
        "0",
        "10000000000",
        "10000000000",
        "100000",
        "100000",
        "100000",
        "100000",
        "large_rawcount",
    ],
    [
        "-246",
        "168300731",
        "2568258242370",
        "410232131549",
        "0",
        "0",
        "0",
        "271891678",
        "145209040",
        "0",
        "0",
        "0",
        "0",
        "bulk_count",
    ],
    [
        "14",
        "5438",
        "3012412853",
        "376555354",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "bulk_count",
    ],
    [
        "16",
        "2340274",
        "7601145",
        "225288",
        "0",
        "0",
        "0",
        "3033012",
        "2099072",
        "0",
        "0",
        "0",
        "0",
        "bulk_count",
    ],
    ["18", "0", "1566", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
    ["20", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
    ["22", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
    [
        "-4",
        "8385014",
        "2787714307906",
        "1171662236873",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "bulk_count",
    ],
    [
        "26",
        "3614",
        "2922261424",
        "833538016",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "bulk_count",
    ],
    ["28", "65262", "442474", "63489", "0", "0", "0", "0", "0", "0", "0", "0", "0", "bulk_count"],
    ["30", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
    ["32", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
    ["34", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
    ["1086", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
    ["1088", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
    ["1090", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "bulk_count"],
    ["1092", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "bulk_count"],
    ["1094", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "large_rawcount"],
]

TEAMING_INPUT: _Block = [
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
        "DAG-NET ",
        "SwitchIndependent ",
        "Dynamic ",
        "85:ae:ac:eb:a5:53;39:d6:c8:28:3f:c7",
        "SLOT 6 Port 1 DAG;SLOT 4 Port 2 DAG",
        "Intel(R) Ethernet 10G 2P X520 Adapter #2;Intel(R) Ethernet 10G 2P X520 Adapter #4",
        "10000000000;10000000000",
        "{07F1904B-3242-4CFE-8D5C-15C174CD3CD5};{CAA71E22-85E1-4D60-8AA9-4D59D470FD18}",
    ],
    [
        "MAPI-NET ",
        "SwitchIndependent ",
        "Dynamic ",
        "f0:23:a7:da:b2:85,13:89:c4:52:a9:13",
        "SLOT 6 Port 2 MAPI;SLOT 4 Port 1 MAPI",
        "Intel(R) Ethernet 10G 2P X520 Adapter;Intel(R) Ethernet 10G 2P X520 Adapter #3",
        "10000000000;10000000000",
        "{F27DD595-90F2-43D7-9853-B76E6ABB3057};{5B3C2733-25B4-452C-80DC-A0B0A7816AFA}",
    ],
    ["[teaming_end]"],
]
WINPERF_IF_WIN32_NETWORKADAPTER_INPUT_2: _Block = [
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
        "PWEX02 ",
        " 4d:4d:ed:4d:0d:1d ",
        " Intel(R) Gigabit 4P I350-t rNDC ",
        " NIC1 ",
        " 2 ",
        " 1000000000 ",
        " {02C3339A-3E06-45A9-B5D4-77AD13199A63}",
    ],
    [
        "PWEX02 ",
        " f9:d5:5b:3d:6d:ee ",
        " Intel(R) Ethernet 10G 2P X520 Adapter ",
        " SLOT 6 Port 2 MAPI ",
        " 2 ",
        "  ",
        " {F27DD595-90F2-43D7-9853-B76E6ABB3057}",
    ],
    [
        "PWEX02 ",
        " 32:59:47:d0:52:26 ",
        " Intel(R) Ethernet 10G 2P X520 Adapter ",
        " SLOT 6 Port 1 DAG ",
        " 2 ",
        "  ",
        " {07F1904B-3242-4CFE-8D5C-15C174CD3CD5}",
    ],
    [
        "PWEX02 ",
        " 82:84:b1:4f:1d:a8 ",
        " Intel(R) Gigabit 4P I350-t rNDC #2 ",
        " NIC2 ",
        " 7 ",
        " 9223372036854775807 ",
        " {B02D91C6-6361-4FD7-B76F-738C0B0A9EA7}",
    ],
    [
        "PWEX02 ",
        " d0:fe:91:ac:30:29 ",
        " Intel(R) Gigabit 4P I350-t rNDC #3 ",
        " NIC3 ",
        " 7 ",
        " 9223372036854775807 ",
        " {5385E65C-5D93-433C-8C47-0450E6086AFD}",
    ],
    [
        "PWEX02 ",
        " 89:cd:72:0a:8f:58 ",
        " Intel(R) Gigabit 4P I350-t rNDC #4 ",
        " NIC4 ",
        " 7 ",
        " 9223372036854775807 ",
        " {C3D7E9E2-D103-4F93-A40B-D6C27A5B93A9}",
    ],
    [
        "PWEX02 ",
        " e7:4e:75:95:06:5c ",
        " Intel(R) Ethernet 10G 2P X520 Adapter ",
        " SLOT 4 Port 1 MAPI ",
        " 2 ",
        "  ",
        " {5B3C2733-25B4-452C-80DC-A0B0A7816AFA}",
    ],
    [
        "PWEX02 ",
        " 48:3b:ed:54:44:3f ",
        " Intel(R) Ethernet 10G 2P X520 Adapter ",
        " SLOT 4 Port 2 DAG ",
        " 2 ",
        "  ",
        " {CAA71E22-85E1-4D60-8AA9-4D59D470FD18}",
    ],
    [
        "PWEX02 ",
        " e7:4e:75:95:06:5c ",
        " Microsoft Network Adapter Multiplexor Driver ",
        " MAPI-NET ",
        " 2 ",
        " 10000000000 ",
        " {A00F44A5-844B-4679-B2BA-0161B98AE717}",
    ],
    [
        "PWEX02 ",
        " 32:59:47:d0:52:26 ",
        " Microsoft Network Adapter Multiplexor Driver #2 ",
        " DAG-NET ",
        " 2 ",
        " 10000000000 ",
        " {09804D64-9D95-4FBF-A8B1-5BE56205FBD8}",
    ],
]

EXPECTED_WINPERF_IF_WIN32_NETWORKADAPTER_OUTPUT_2: Sequence[AdditionalIfData] = [
    AdditionalIfData(
        name="Intel(R) Gigabit 4P I350-t rNDC",
        alias="NIC1",
        speed=1000000000,
        oper_status="1",
        oper_status_name="up",
        mac_address="4d:4d:ed:4d:0d:1d",
        guid="{02C3339A-3E06-45A9-B5D4-77AD13199A63}",
    ),
    AdditionalIfData(
        name="Intel(R) Ethernet 10G 2P X520 Adapter",
        alias="SLOT 6 Port 2 MAPI",
        speed=0,
        oper_status="1",
        oper_status_name="up",
        mac_address="f9:d5:5b:3d:6d:ee",
        guid="{F27DD595-90F2-43D7-9853-B76E6ABB3057}",
    ),
    AdditionalIfData(
        name="Intel(R) Ethernet 10G 2P X520 Adapter",
        alias="SLOT 6 Port 1 DAG",
        speed=0,
        oper_status="1",
        oper_status_name="up",
        mac_address="32:59:47:d0:52:26",
        guid="{07F1904B-3242-4CFE-8D5C-15C174CD3CD5}",
    ),
    AdditionalIfData(
        name="Intel(R) Gigabit 4P I350-t rNDC #2",
        alias="NIC2",
        speed=0,
        oper_status="7",
        oper_status_name="Media disconnected",
        mac_address="82:84:b1:4f:1d:a8",
        guid="{B02D91C6-6361-4FD7-B76F-738C0B0A9EA7}",
    ),
    AdditionalIfData(
        name="Intel(R) Gigabit 4P I350-t rNDC #3",
        alias="NIC3",
        speed=0,
        oper_status="7",
        oper_status_name="Media disconnected",
        mac_address="d0:fe:91:ac:30:29",
        guid="{5385E65C-5D93-433C-8C47-0450E6086AFD}",
    ),
    AdditionalIfData(
        name="Intel(R) Gigabit 4P I350-t rNDC #4",
        alias="NIC4",
        speed=0,
        oper_status="7",
        oper_status_name="Media disconnected",
        mac_address="89:cd:72:0a:8f:58",
        guid="{C3D7E9E2-D103-4F93-A40B-D6C27A5B93A9}",
    ),
    AdditionalIfData(
        name="Intel(R) Ethernet 10G 2P X520 Adapter",
        alias="SLOT 4 Port 1 MAPI",
        speed=0,
        oper_status="1",
        oper_status_name="up",
        mac_address="e7:4e:75:95:06:5c",
        guid="{5B3C2733-25B4-452C-80DC-A0B0A7816AFA}",
    ),
    AdditionalIfData(
        name="Intel(R) Ethernet 10G 2P X520 Adapter",
        alias="SLOT 4 Port 2 DAG",
        speed=0,
        oper_status="1",
        oper_status_name="up",
        mac_address="48:3b:ed:54:44:3f",
        guid="{CAA71E22-85E1-4D60-8AA9-4D59D470FD18}",
    ),
    AdditionalIfData(
        name="Microsoft Network Adapter Multiplexor Driver",
        alias="MAPI-NET",
        speed=10000000000,
        oper_status="1",
        oper_status_name="up",
        mac_address="e7:4e:75:95:06:5c",
        guid="{A00F44A5-844B-4679-B2BA-0161B98AE717}",
    ),
    AdditionalIfData(
        name="Microsoft Network Adapter Multiplexor Driver #2",
        alias="DAG-NET",
        speed=10000000000,
        oper_status="1",
        oper_status_name="up",
        mac_address="32:59:47:d0:52:26",
        guid="{09804D64-9D95-4FBF-A8B1-5BE56205FBD8}",
    ),
]

WINPERF_IF_WIN32_NETWORKADAPTER_INPUT_1: _Block = [
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
        "TBWAW-VEEAM01",
        "63:fc:b4:9a:ae:63 ",
        "IBM USB Remote NDIS   Network Device        #2 ",
        "Local Area Connection 2 ",
        "2 ",
        "9728000 ",
        "{24AA204E-C3FE-47E8-A890-3C1D7584FAF6}",
    ],
    [
        "TBWAW-VEEAM01",
        "c3:08:87:2e:16:89 ",
        "Intel(R) I350 Gigabit Network Connection ",
        "Ethernet 3 ",
        "7 ",
        "9223372036854775807 ",
        "{2FCFD4C6-B7C6-40CB-8336-385865CA8822}",
    ],
    [
        "TBWAW-VEEAM01",
        "94:4f:82:20:86:50 ",
        "Intel(R) I350 Gigabit Network Connection #2 ",
        "Ethernet 4 ",
        "7 ",
        "9223372036854775807 ",
        "{C28247BA-9E89-4F4F-8B42-6637D507B1A2}",
    ],
    [
        "TBWAW-VEEAM01",
        "71:0d:d9:6a:50:aa ",
        "Intel(R) I350 Gigabit Network Connection #3 ",
        "Ethernet 5 ",
        "7 ",
        "9223372036854775807 ",
        "{3A8F46C0-2BC8-4BB2-8C61-64ED8BC5B76E}",
    ],
    [
        "TBWAW-VEEAM01",
        "c4:70:14:5f:d2:c0 ",
        "Intel(R) I350 Gigabit Network Connection #4 ",
        "Ethernet 6 ",
        "7 ",
        "9223372036854775807 ",
        "{2443DE70-0A53-4936-A561-7C6DBFE28631}",
    ],
    [
        "TBWAW-VEEAM01",
        "38:4c:78:cc:d7:51 ",
        "QLogic 1/10GbE Server Adapter ",
        "Ethernet 2 ",
        "2 ",
        " ",
        "{4E16E6AC-F88A-4D51-9620-711DBB7B0015}",
    ],
    [
        "TBWAW-VEEAM01",
        "1e:03:f0:24:5c:ce ",
        "QLogic 1/10GbE Server Adapter ",
        "Ethernet ",
        "1 ",
        " ",
        "{0A2E026F-F059-43CA-AA66-E77FC40EF702}",
    ],
    [
        "TBWAW-VEEAM01",
        "38:4c:78:cc:d7:51 ",
        "Microsoft Network Adapter Multiplexor Driver ",
        "LAN ",
        "2 ",
        "20000000000 ",
        "{2EBF040F-4EA6-4F38-B743-1B4A7BC02F30}",
    ],
]

EXPECTED_WINPERF_IF_WIN32_NETWORKADAPTER_OUTPUT_1: Sequence[AdditionalIfData] = [
    AdditionalIfData(
        name="IBM USB Remote NDIS Network Device #2",
        alias="Local Area Connection 2",
        speed=9728000,
        oper_status="1",
        oper_status_name="up",
        mac_address="63:fc:b4:9a:ae:63",
        guid="{24AA204E-C3FE-47E8-A890-3C1D7584FAF6}",
    ),
    AdditionalIfData(
        name="Intel(R) I350 Gigabit Network Connection",
        alias="Ethernet 3",
        speed=0,
        oper_status="7",
        oper_status_name="Media disconnected",
        mac_address="c3:08:87:2e:16:89",
        guid="{2FCFD4C6-B7C6-40CB-8336-385865CA8822}",
    ),
    AdditionalIfData(
        name="Intel(R) I350 Gigabit Network Connection #2",
        alias="Ethernet 4",
        speed=0,
        oper_status="7",
        oper_status_name="Media disconnected",
        mac_address="94:4f:82:20:86:50",
        guid="{C28247BA-9E89-4F4F-8B42-6637D507B1A2}",
    ),
    AdditionalIfData(
        name="Intel(R) I350 Gigabit Network Connection #3",
        alias="Ethernet 5",
        speed=0,
        oper_status="7",
        oper_status_name="Media disconnected",
        mac_address="71:0d:d9:6a:50:aa",
        guid="{3A8F46C0-2BC8-4BB2-8C61-64ED8BC5B76E}",
    ),
    AdditionalIfData(
        name="Intel(R) I350 Gigabit Network Connection #4",
        alias="Ethernet 6",
        speed=0,
        oper_status="7",
        oper_status_name="Media disconnected",
        mac_address="c4:70:14:5f:d2:c0",
        guid="{2443DE70-0A53-4936-A561-7C6DBFE28631}",
    ),
    AdditionalIfData(
        name="QLogic 1/10GbE Server Adapter",
        alias="Ethernet 2",
        speed=0,
        oper_status="1",
        oper_status_name="up",
        mac_address="38:4c:78:cc:d7:51",
        guid="{4E16E6AC-F88A-4D51-9620-711DBB7B0015}",
    ),
    AdditionalIfData(
        name="QLogic 1/10GbE Server Adapter",
        alias="Ethernet",
        speed=0,
        oper_status="2",
        oper_status_name="Connecting",
        mac_address="1e:03:f0:24:5c:ce",
        guid="{0A2E026F-F059-43CA-AA66-E77FC40EF702}",
    ),
    AdditionalIfData(
        name="Microsoft Network Adapter Multiplexor Driver",
        alias="LAN",
        speed=20000000000,
        oper_status="1",
        oper_status_name="up",
        mac_address="38:4c:78:cc:d7:51",
        guid="{2EBF040F-4EA6-4F38-B743-1B4A7BC02F30}",
    ),
]


def _entry(
    num: int,
    name: Names,
    speed: int,
    mode: Mode = Mode.UP,
    *,
    alias: str | None = None,
    phys_address: str | None = None,
) -> interfaces.InterfaceWithCounters:
    return interfaces.InterfaceWithCounters(
        _if_attributes(num, name, speed, mode=mode, alias=alias, phys_address=phys_address),
        _counters.get(name, null_counters),
    )


def _flatten(data: Sequence[_Block]) -> _Block:
    return [element for block in data for element in block]


@pytest.mark.parametrize(
    "string_table, section",
    [
        pytest.param(
            _flatten(
                [
                    VALID_ONE_IF_INPUT,
                    DHCP_STRANGE_INPUT,
                    [
                        ["2002", "2", "text"],
                        ["2006", "01:02:03:04:05:06", "text"],
                    ],
                ]
            ),
            SectionCounters(
                timestamp=1630928323.48,
                interfaces={
                    str(Names.INTEL_PRO): interfaces.InterfaceWithCounters(
                        _if_attributes(
                            1,
                            Names.INTEL_PRO,
                            1000000000,
                            mode=Mode.DOWN,
                            phys_address="\x01\x02\x03\x04\x05\x06",
                        ),
                        _counters[Names.INTEL_PRO],
                    ),
                },
                found_windows_if=False,
                found_mk_dhcp_enabled=True,
            ),
            id="single interface with legacy plug-in data, status and mac",
        )
    ],
)
def test_parse_winperf_if_ex(
    string_table: StringTable,
    section: SectionCounters,
) -> None:
    assert parse_winperf_if(string_table) == section


@pytest.mark.parametrize(
    "string_table, section",
    [
        pytest.param(
            VALID_ONE_IF_INPUT,
            SectionCounters(
                timestamp=1630928323.48,
                interfaces={
                    str(name): _entry(i + 1, name, speed)
                    for i, (name, speed) in enumerate([(Names.INTEL_PRO, 1000000000)])
                },
                found_windows_if=False,
                found_mk_dhcp_enabled=False,
            ),
            id="single interface",
        ),
        pytest.param(
            _flatten([VALID_ONE_IF_INPUT, DHCP_STRANGE_INPUT, [["2002", "1", "text"]]]),
            SectionCounters(
                timestamp=1630928323.48,
                interfaces={
                    str(name): _entry(i + 1, name, speed)
                    for i, (name, speed) in enumerate([(Names.INTEL_PRO, 1000000000)])
                },
                found_windows_if=False,
                found_mk_dhcp_enabled=True,
            ),
            id="single interface with legacy plug-in data and pseudo counter",
        ),
        pytest.param(
            MULTIPLY_INTERFACES_INPUT,
            SectionCounters(
                timestamp=1425370325.75,
                interfaces={
                    str(name): _entry(i + 1, name, speed)
                    for i, (name, speed) in enumerate(
                        [
                            (Names.QLOGIC_2, 10000000000),
                            (Names.QLOGIC, 10000000000),
                            (Names.INTEL_I350, 0),
                            (Names.INTEL_I350_2, 0),
                            (Names.INTEL_I350_3, 0),
                            (Names.INTEL_I350_4, 0),
                            (Names.IBM_USB_2, 9728000),
                            (Names.ISATAP_24, 100000),
                            (Names.ISATAP_2E, 100000),
                        ]
                    )
                },
                found_windows_if=False,
                found_mk_dhcp_enabled=False,
            ),
            id="multiple interfaces",
        ),
        pytest.param(
            _flatten(
                [
                    MULTIPLY_INTERFACES_12_INPUT,
                    TEAMING_INPUT,
                    WINPERF_IF_WIN32_NETWORKADAPTER_INPUT_2,
                ]
            ),
            SectionCounters(
                timestamp=1498114570.1,
                interfaces={
                    str(name): _entry(i + 1, name, speed)
                    for i, (name, speed) in enumerate(
                        [
                            (Names.INTEL_NDC, 1000000000),
                            (Names.INTEL_X520, 10000000000),
                            (Names.INTEL_X520_2, 10000000000),
                            (Names.INTEL_NDC_2, 0),
                            (Names.INTEL_NDC_3, 0),
                            (Names.INTEL_NDC_4, 0),
                            (Names.INTEL_X520_3, 10000000000),
                            (Names.INTEL_X520_4, 10000000000),
                            (Names.ISA, 100000),
                            (Names.ISATAP_A0, 100000),
                            (Names.ISATAP_09, 100000),
                            (Names.ISATAP_BF, 100000),
                        ]
                    )
                },
                found_windows_if=True,
                found_mk_dhcp_enabled=False,
            ),
            id="multiple interfaces with legacy plug-in data",
        ),
    ],
)
def test_parse_winperf_if(
    string_table: StringTable,
    section: SectionCounters,
) -> None:
    assert parse_winperf_if(string_table) == section


@pytest.mark.parametrize(
    "string_table, section",
    [
        pytest.param(
            [
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
                    "DAG-NET ",
                    "SwitchIndependent ",
                    "Dynamic ",
                    "85:ae:ac:eb:a5:53;39:d6:c8:28:3f:c7",
                    "SLOT 6 Port 1 DAG;SLOT 4 Port 2 DAG",
                    "Intel(R) Ethernet 10G 2P X520 Adapter     #2;Intel(R) Ethernet 10G 2P X520 Adapter   #4",
                    "10000000000;10000000000",
                    "{07F1904B-3242-4CFE-8D5C-15C174CD3CD5};{CAA71E22-85E1-4D60-8AA9-4D59D470FD18}",
                ],
                [
                    "MAPI-NET ",
                    "SwitchIndependent ",
                    "Dynamic ",
                    "13:89:c4:52:a9:13;4c:98:fb:4c:8f:c6",
                    "SLOT 6 Port 2 MAPI;SLOT 4 Port 1 MAPI",
                    "Intel(R) Ethernet 10G 2P X520 Adapter;Intel(R) Ethernet 10G 2P X520 Adapter #3",
                    "10000000000;10000000000",
                    "{F27DD595-90F2-43D7-9853-B76E6ABB3057};{5B3C2733-25B4-452C-80DC-A0B0A7816AFA}",
                ],
            ],
            {
                "{07F1904B-3242-4CFE-8D5C-15C174CD3CD5}": TeamingData(
                    team_name="DAG-NET",
                    name="Intel(R) Ethernet 10G 2P X520 Adapter #2",
                ),
                "{CAA71E22-85E1-4D60-8AA9-4D59D470FD18}": TeamingData(
                    team_name="DAG-NET",
                    name="Intel(R) Ethernet 10G 2P X520 Adapter #4",
                ),
                "{F27DD595-90F2-43D7-9853-B76E6ABB3057}": TeamingData(
                    team_name="MAPI-NET",
                    name="Intel(R) Ethernet 10G 2P X520 Adapter",
                ),
                "{5B3C2733-25B4-452C-80DC-A0B0A7816AFA}": TeamingData(
                    team_name="MAPI-NET",
                    name="Intel(R) Ethernet 10G 2P X520 Adapter #3",
                ),
            },
        ),
        pytest.param(
            [
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
                    "PVSMWTeam ",
                    "Lacp ",
                    "Dynamic ",
                    "4a:10:45:0b:42:85;e8:5d:43:89:fc:36",
                    "Ethernet 3;Ethernet 6",
                    "HP NC523SFP 10Gb 2-port Server Adapter;HP NC523SFP 10Gb 2-port Server Adapter #3",
                    "10000000000;10000000000",
                    "{0DB3EDD7-7556-4C2F-912E-2DA7902FF40A};{9E6FF8D7-B45D-4A39-A063-BEED584A4A54}",
                ],
                [
                    "SRVMWTeam ",
                    "Lacp ",
                    "Dynamic ",
                    "c6:27:f6:2a:c2:20;b1:df:cd:c2:9b:3b",
                    "Ethernet 7;Ethernet 5",
                    "HP NC382i DP Multifunction Gigabit Server Adapter #52;HP NC382i DP Multifunction Gigabit Server Adapter #53",
                    "1000000000;1000000000",
                    "{5EC6AE42-0E76-4EC1-A081-8EBA8C27A7F6};{51673C8C-251D-4DF1-8AB2-97452DC1355D}",
                ],
            ],
            {
                "{0DB3EDD7-7556-4C2F-912E-2DA7902FF40A}": TeamingData(
                    team_name="PVSMWTeam",
                    name="HP NC523SFP 10Gb 2-port Server Adapter",
                ),
                "{9E6FF8D7-B45D-4A39-A063-BEED584A4A54}": TeamingData(
                    team_name="PVSMWTeam",
                    name="HP NC523SFP 10Gb 2-port Server Adapter #3",
                ),
                "{5EC6AE42-0E76-4EC1-A081-8EBA8C27A7F6}": TeamingData(
                    team_name="SRVMWTeam",
                    name="HP NC382i DP Multifunction Gigabit Server Adapter #52",
                ),
                "{51673C8C-251D-4DF1-8AB2-97452DC1355D}": TeamingData(
                    team_name="SRVMWTeam",
                    name="HP NC382i DP Multifunction Gigabit Server Adapter #53",
                ),
            },
        ),
        pytest.param(
            [
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
                    "Lacp ",
                    "Dynamic ",
                    "1e:03:f0:24:5c:ce;38:4c:78:cc:d7:51",
                    "Ethernet;Ethernet 2",
                    "QLogic 1/10GbE Server Adapter #2;QLogic 1/10GbE Server Adapter",
                    "10000000000;10000000000",
                    "{0A2E026F-F059-43CA-AA66-E77FC40EF702};{4E16E6AC-F88A-4D51-9620-711DBB7B0015}",
                ],
            ],
            {
                "{0A2E026F-F059-43CA-AA66-E77FC40EF702}": TeamingData(
                    team_name="LAN",
                    name="QLogic 1/10GbE Server Adapter #2",
                ),
                "{4E16E6AC-F88A-4D51-9620-711DBB7B0015}": TeamingData(
                    team_name="LAN",
                    name="QLogic 1/10GbE Server Adapter",
                ),
            },
        ),
    ],
)
def test_parse_winperf_if_teaming(
    string_table: StringTable,
    section: SectionTeaming,
) -> None:
    assert parse_winperf_if_teaming(string_table) == section


@pytest.mark.parametrize(
    "string_table, section",
    [
        pytest.param(
            WINPERF_IF_WIN32_NETWORKADAPTER_INPUT_1,
            EXPECTED_WINPERF_IF_WIN32_NETWORKADAPTER_OUTPUT_1,
            id="windows_if.ps1 1",
        ),
        pytest.param(
            WINPERF_IF_WIN32_NETWORKADAPTER_INPUT_2,
            EXPECTED_WINPERF_IF_WIN32_NETWORKADAPTER_OUTPUT_2,
            id="windows_if.ps1 2",
        ),
        pytest.param(
            [
                ["Node", "MACAddress", "Name", "NetConnectionID", "NetConnectionStatus"],
                ["Z3127130", "", "WAN Miniport (L2TP)", "", ""],  # do not skip
                ["Z3127130", "31:0b:d4:9c:ef:59", "Broadcom OK 1", "NIC2", "2"],
                ["Z3127130", "", "Broadcom XX Skip", "NIC4", "4"],
                ["Z3127130", "ee:17:bb:db:42:fa", "Broadcom OK 2", "NIC1", "2"],
            ],
            [
                AdditionalIfData(
                    name="WAN Miniport (L2TP)",
                    alias="",
                    speed=0,
                    oper_status="2",
                    oper_status_name="down",
                    mac_address="",
                    guid=None,
                ),
                AdditionalIfData(
                    name="Broadcom OK 1",
                    alias="NIC2",
                    speed=0,
                    oper_status="1",
                    oper_status_name="up",
                    mac_address="31:0b:d4:9c:ef:59",
                    guid=None,
                ),
                AdditionalIfData(
                    name="Broadcom OK 2",
                    alias="NIC1",
                    speed=0,
                    oper_status="1",
                    oper_status_name="up",
                    mac_address="ee:17:bb:db:42:fa",
                    guid=None,
                ),
            ],
            id="wmic_if.bat",
        ),
    ],
)
def test_parse_winperf_if_win32_networkadapter(
    string_table: StringTable,
    section: SectionExtended,
) -> None:
    assert parse_winperf_if_win32_networkadapter(string_table) == section


def test_parse_winperf_if_get_netadapter() -> None:
    # tested strange _canonize_name too
    assert parse_winperf_if_get_netadapter(
        [
            [
                "WAN_Miniport__(Network Monitor) ",
                "Local Area Connection* 8",
                "",  # expected speed 0
                "1",
                "Up",
                "",
                "{F71AF561-CF55-47EE-A803-3F05F2EDFD65}",
            ],
            [
                "Intel(R) PRO/1000 MT Desktop Adapter_",
                "Ethernet",
                "999",
                "1",
                "Up",
                "7e-e6-cc-09-c3-c8",
                "{570809B4-FDEF-4479-9DEE-1E263EA4166F}",
            ],
        ]
    ) == [
        AdditionalIfData(
            name="WAN Miniport (Network Monitor)",
            alias="Local Area Connection* 8",
            speed=0,
            oper_status="1",
            oper_status_name="Up",
            mac_address="",
            guid="{F71AF561-CF55-47EE-A803-3F05F2EDFD65}",
        ),
        AdditionalIfData(
            name="Intel(R) PRO/1000 MT Desktop Adapter",
            alias="Ethernet",
            speed=999,
            oper_status="1",
            oper_status_name="Up",
            mac_address="7e:e6:cc:09:c3:c8",
            guid="{570809B4-FDEF-4479-9DEE-1E263EA4166F}",
        ),
    ]


def test_parse_winperf_if_dhcp() -> None:
    assert parse_winperf_if_dhcp(
        [
            ["Description", "DHCPEnabled"],
            ["Microsoft", "Kernel", "Debug", "Network", "Adapter", "TRUE"],
            ["Intel(R)", "PRO/1000", "MT", "Desktop", "Adapter", "TRUE"],
            ["WAN", "Miniport", "(SSTP)", "FALSE"],
            ["WAN", "Miniport", "(Network", "Monitor)", "FALSE"],
        ]
    ) == [
        {
            "DHCPEnabled": "TRUE",
            "Description": "Microsoft Kernel Debug Network Adapter",
        },
        {
            "DHCPEnabled": "TRUE",
            "Description": "Intel(R) PRO/1000 MT Desktop Adapter",
        },
        {
            "DHCPEnabled": "FALSE",
            "Description": "WAN Miniport (SSTP)",
        },
        {
            "DHCPEnabled": "FALSE",
            "Description": "WAN Miniport (Network Monitor)",
        },
    ]


@pytest.mark.parametrize(
    "interfaces_in, section_teaming, section_extended, interfaces_out",
    [
        pytest.param(
            {Names.INTEL_PRO: _entry(1, Names.INTEL_PRO, 1000000000)},
            None,
            None,
            [_entry(1, Names.INTEL_PRO, 1000000000)],
            id="agent data only",
        ),
        pytest.param(
            {
                Names.QLOGIC_2: _entry(1, Names.QLOGIC_2, 10000000000),
                Names.QLOGIC: _entry(2, Names.QLOGIC, 10000000000),
                Names.INTEL_I350: _entry(3, Names.INTEL_I350, 0),
                Names.INTEL_I350_2: _entry(4, Names.INTEL_I350_2, 0),
                Names.INTEL_I350_3: _entry(5, Names.INTEL_I350_3, 0),
                Names.INTEL_I350_4: _entry(6, Names.INTEL_I350_4, 0),
                Names.IBM_USB_2: _entry(7, Names.IBM_USB_2, 9728000),
                Names.ISATAP_24: _entry(8, Names.ISATAP_24, 100000),
                Names.ISATAP_2E: _entry(9, Names.ISATAP_2E, 100000),
            },
            None,
            EXPECTED_WINPERF_IF_WIN32_NETWORKADAPTER_OUTPUT_1,
            [
                _entry(1, Names.QLOGIC_2, 10000000000),
                _entry(
                    2,
                    Names.QLOGIC,
                    10000000000,
                    Mode.UP,
                    alias="Ethernet 2",
                    phys_address="8LxÌ×Q",
                ),
                _entry(
                    3,
                    Names.INTEL_I350,
                    0,
                    Mode.DISCONN,
                    alias="Ethernet 3",
                    phys_address="Ã\x08\x87.\x16\x89",
                ),
                _entry(
                    4,
                    Names.INTEL_I350_2,
                    0,
                    Mode.DISCONN,
                    alias="Ethernet 4",
                    phys_address="\x94O\x82 \x86P",
                ),
                _entry(
                    5,
                    Names.INTEL_I350_3,
                    0,
                    Mode.DISCONN,
                    alias="Ethernet 5",
                    phys_address="q\rÙjPª",
                ),
                _entry(
                    6,
                    Names.INTEL_I350_4,
                    0,
                    Mode.DISCONN,
                    alias="Ethernet 6",
                    phys_address="Äp\x14_ÒÀ",
                ),
                _entry(
                    7,
                    Names.IBM_USB_2,
                    9728000,
                    Mode.UP,
                    alias="Local Area Connection 2",
                    phys_address="cü´\x9a®c",
                ),
                _entry(8, Names.ISATAP_24, 100000),
                _entry(9, Names.ISATAP_2E, 100000),
            ],
            id="with additional data",
        ),
        pytest.param(
            {
                Names.INTEL_NDC: _entry(1, Names.INTEL_NDC, 1000000000),
                Names.INTEL_X520: _entry(2, Names.INTEL_X520, 10000000000),
                Names.INTEL_X520_2: _entry(3, Names.INTEL_X520_2, 10000000000),
                Names.INTEL_NDC_2: _entry(4, Names.INTEL_NDC_2, 0),
                Names.INTEL_NDC_3: _entry(5, Names.INTEL_NDC_3, 0),
                Names.INTEL_NDC_4: _entry(6, Names.INTEL_NDC_4, 0),
                Names.INTEL_X520_3: _entry(7, Names.INTEL_X520_3, 10000000000),
                Names.INTEL_X520_4: _entry(8, Names.INTEL_X520_4, 10000000000),
                Names.ISA: _entry(9, Names.ISA, 100000),
                Names.ISATAP_A0: _entry(10, Names.ISATAP_A0, 100000),
                Names.ISATAP_09: _entry(11, Names.ISATAP_09, 100000),
                Names.ISATAP_BF: _entry(12, Names.ISATAP_BF, 100000),
            },
            {
                "{07F1904B-3242-4CFE-8D5C-15C174CD3CD5}": TeamingData(
                    team_name="DAG-NET",
                    name="Intel(R) Ethernet 10G 2P X520 Adapter #2",
                ),
                "{CAA71E22-85E1-4D60-8AA9-4D59D470FD18}": TeamingData(
                    team_name="DAG-NET",
                    name="Intel(R) Ethernet 10G 2P X520 Adapter #4",
                ),
                "{F27DD595-90F2-43D7-9853-B76E6ABB3057}": TeamingData(
                    team_name="MAPI-NET",
                    name="Intel(R) Ethernet 10G 2P X520 Adapter",
                ),
                "{5B3C2733-25B4-452C-80DC-A0B0A7816AFA}": TeamingData(
                    team_name="MAPI-NET",
                    name="Intel(R) Ethernet 10G 2P X520 Adapter #3",
                ),
            },
            EXPECTED_WINPERF_IF_WIN32_NETWORKADAPTER_OUTPUT_2,
            [
                _entry(
                    1,
                    Names.INTEL_NDC,
                    1000000000,
                    Mode.UP,
                    alias="NIC1",
                    phys_address="MMíM\r\x1d",
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="2",
                        descr=Names.INTEL_X520,
                        alias="SLOT 6 Port 2 MAPI",
                        type="6",
                        speed=10000000000,
                        oper_status="1",
                        out_qlen=0,
                        phys_address="ùÕ[=mî",
                        oper_status_name="up",
                        speed_as_text="",
                        group="MAPI-NET",
                        node=None,
                        admin_status=None,
                    ),
                    _counters[Names.INTEL_X520],
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="3",
                        descr=Names.INTEL_X520_2,
                        alias="SLOT 6 Port 1 DAG",
                        type="6",
                        speed=10000000000,
                        oper_status="1",
                        out_qlen=0,
                        phys_address="2YGÐR&",
                        oper_status_name="up",
                        speed_as_text="",
                        group="DAG-NET",
                        node=None,
                        admin_status=None,
                    ),
                    _counters[Names.INTEL_X520_2],
                ),
                _entry(
                    4,
                    Names.INTEL_NDC_2,
                    0,
                    mode=Mode.DISCONN,
                    alias="NIC2",
                    phys_address="\x82\x84±O\x1d¨",
                ),
                _entry(
                    5,
                    Names.INTEL_NDC_3,
                    0,
                    mode=Mode.DISCONN,
                    alias="NIC3",
                    phys_address="Ðþ\x91¬0)",
                ),
                _entry(
                    6,
                    Names.INTEL_NDC_4,
                    0,
                    mode=Mode.DISCONN,
                    alias="NIC4",
                    phys_address="\x89Ír\n\x8fX",
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="7",
                        descr=Names.INTEL_X520_3,
                        alias="SLOT 4 Port 1 MAPI",
                        type="6",
                        speed=10000000000,
                        oper_status="1",
                        out_qlen=0,
                        phys_address="çNu\x95\x06\\",
                        oper_status_name="up",
                        speed_as_text="",
                        group="MAPI-NET",
                        node=None,
                        admin_status=None,
                    ),
                    _counters[Names.INTEL_X520_3],
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="8",
                        descr=Names.INTEL_X520_4,
                        alias="SLOT 4 Port 2 DAG",
                        type="6",
                        speed=10000000000,
                        oper_status="1",
                        out_qlen=0,
                        phys_address="H;íTD?",
                        oper_status_name="up",
                        speed_as_text="",
                        group="DAG-NET",
                        node=None,
                        admin_status=None,
                    ),
                    _counters[Names.INTEL_X520_4],
                ),
                _entry(9, Names.ISA, 100000),
                _entry(10, Names.ISATAP_A0, 100000),
                _entry(11, Names.ISATAP_09, 100000),
                _entry(12, Names.ISATAP_BF, 100000),
            ],
            id="with additional data",
        ),
    ],
)
def test_merge_sections(
    interfaces_in: Mapping[str, interfaces.InterfaceWithCounters],
    section_teaming: SectionTeaming | None,
    section_extended: SectionExtended | None,
    interfaces_out: interfaces.Section[interfaces.InterfaceWithCounters],
) -> None:
    assert (
        _merge_sections(
            interfaces_in,
            section_teaming,
            section_extended,
        )
        == interfaces_out
    )


@pytest.mark.parametrize(
    "item, result",
    [
        pytest.param(
            Names.INTEL_PRO,
            Result(
                state=State.WARN,
                summary="DHCP: enabled",
            ),
            id="dhcp on",
        ),
        pytest.param(
            "WAN Miniport [SSTP]",
            Result(
                state=State.OK,
                summary="DHCP: disabled",
            ),
            id="dhcp off",
        ),
        pytest.param(
            "wrong",
            None,
            id="no item match",
        ),
    ],
)
def test_check_dhcp(item: str, result: Result | None) -> None:
    assert (
        _check_dhcp(
            item,
            [
                Names.INTEL_PRO,
                "WAN Miniport [SSTP]",
            ],
            [
                {
                    "DHCPEnabled": "TRUE",
                    "Description": "Microsoft Kernel Debug Network Adapter",
                },
                {
                    "DHCPEnabled": "TRUE",
                    "Description": "Intel(R) PRO/1000 MT Desktop Adapter",
                },
                {
                    "DHCPEnabled": "FALSE",
                    "Description": "WAN Miniport (SSTP)",
                },
                {
                    "DHCPEnabled": "FALSE",
                    "Description": "WAN Miniport (IKEv2)",
                },
            ],
        )
        == result
    )


def test_inventory_winperf_if() -> None:
    assert list(
        inventory_winperf_if(
            SectionCounters(
                timestamp=1425370325.75,
                interfaces={
                    Names.QLOGIC_2: _entry(1, Names.QLOGIC_2, 10000000000),
                    Names.QLOGIC: _entry(
                        2,
                        Names.QLOGIC,
                        10000000000,
                        Mode.UP,
                        alias="Ethernet 2",
                        phys_address="QC2I7y",
                    ),
                    Names.INTEL_I350: _entry(
                        3,
                        Names.INTEL_I350,
                        0,
                        Mode.DISCONN,
                        alias="Ethernet 3",
                        phys_address="42oV#!",
                    ),
                    Names.INTEL_I350_2: _entry(
                        4,
                        Names.INTEL_I350_2,
                        0,
                        Mode.DISCONN,
                        alias="Ethernet 4",
                        phys_address="@cZ7ff",
                    ),
                    Names.IBM_USB_2: _entry(
                        7,
                        Names.IBM_USB_2,
                        9728000,
                        Mode.UP,
                        alias="Local Area Connection 2",
                        phys_address="gJ7F^9",
                    ),
                    Names.ISATAP_24: _entry(8, Names.ISATAP_24, 100000),
                },
                found_windows_if=False,
                found_mk_dhcp_enabled=False,
            ),
            None,
            None,
        )
    ) == [
        TableRow(
            path=["networking", "interfaces"],
            key_columns={
                "index": 1,
            },
            inventory_columns={
                "description": "QLogic 1 10GbE Server Adapter 2",
                "alias": "QLogic 1 10GbE Server Adapter 2",
                "speed": 10000000000,
                "phys_address": "",
                "oper_status": 1,
                "port_type": 6,
                "available": False,
            },
            status_columns={},
        ),
        TableRow(
            path=["networking", "interfaces"],
            key_columns={
                "index": 2,
            },
            inventory_columns={
                "description": "QLogic 1 10GbE Server Adapter",
                "alias": "Ethernet 2",
                "speed": 10000000000,
                "phys_address": "51:43:32:49:37:79",
                "oper_status": 1,
                "port_type": 6,
                "available": False,
            },
            status_columns={},
        ),
        TableRow(
            path=["networking", "interfaces"],
            key_columns={
                "index": 7,
            },
            inventory_columns={
                "description": "IBM USB Remote NDIS Network Device 2",
                "alias": "Local Area Connection 2",
                "speed": 9728000,
                "phys_address": "67:4A:37:46:5E:39",
                "oper_status": 1,
                "port_type": 6,
                "available": False,
            },
            status_columns={},
        ),
        TableRow(
            path=["networking", "interfaces"],
            key_columns={
                "index": 8,
            },
            inventory_columns={
                "description": "isatap.{24AA204E-C3FE-47E8-A890-3C1D7584FAF6}",
                "alias": "isatap.{24AA204E-C3FE-47E8-A890-3C1D7584FAF6}",
                "speed": 100000,
                "phys_address": "",
                "oper_status": 1,
                "port_type": 6,
                "available": False,
            },
            status_columns={},
        ),
        Attributes(
            path=["networking"],
            inventory_attributes={
                "available_ethernet_ports": 0,
                "total_ethernet_ports": 4,
                "total_interfaces": 6,
            },
            status_attributes={},
        ),
    ]
