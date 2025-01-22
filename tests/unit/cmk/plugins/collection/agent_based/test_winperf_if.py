#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Final

import pytest

from cmk.agent_based.v2 import Attributes, Result, State, StringTable, TableRow
from cmk.plugins.collection.agent_based.winperf_if import (
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
from cmk.plugins.lib import interfaces

from .utils_inventory import sort_inventory_result


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
    ISATAP_A4 = "isatap.{A447D54F-0E4B-40B3-9FBA-228F7DCE8FC7}"
    ISATAP_4F = "isatap.{4FCE4C48-6217-465A-B807-B61499AE570C}"
    ISATAP_01 = "isatap.{0143C2F2-BFF1-4839-8766-82C6EB3FC440}"
    ISATAP_16 = "isatap.{16377083-0A9A-456B-AB35-9A37E78B3FD4}"
    ISATAP_7A = "isatap.{7A093D2B-D64D-43DF-A0F6-050996EE8D9A}"
    NIN = "isatap.corp.nintendo.eu"


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
        "isatap.{A447D54F-0E4B-40B3-9FBA-228F7DCE8FC7}",
        "isatap.{4FCE4C48-6217-465A-B807-B61499AE570C}",
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
        "isatap.corp.nintendo.eu",
        "isatap.{0143C2F2-BFF1-4839-8766-82C6EB3FC440}",
        "isatap.{16377083-0A9A-456B-AB35-9A37E78B3FD4}",
        "isatap.{7A093D2B-D64D-43DF-A0F6-050996EE8D9A}",
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
        "40:90:7C:1A:45:F8;7C:33:82:DE:F6:3A",
        "SLOT 6 Port 1 DAG;SLOT 4 Port 2 DAG",
        "Intel(R) Ethernet 10G 2P X520 Adapter #2;Intel(R) Ethernet 10G 2P X520 Adapter #4",
        "10000000000;10000000000",
        "{70F3DEC7-8347-4157-B066-95F5672F39BA};{9C4971CB-95AA-4B01-B828-F61B339E4F19}",
    ],
    [
        "MAPI-NET ",
        "SwitchIndependent ",
        "Dynamic ",
        "C4:B7:2C:2A:7C:43;5C:74:5B:97:33:7D",
        "SLOT 6 Port 2 MAPI;SLOT 4 Port 1 MAPI",
        "Intel(R) Ethernet 10G 2P X520 Adapter;Intel(R) Ethernet 10G 2P X520 Adapter #3",
        "10000000000;10000000000",
        "{4C88A19B-5EE4-44A6-ACBB-262131EE1560};{9BD62095-22A8-49CA-BA8B-A7846C6B5FDB}",
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
        " C6:E0:D0:A9:38:87 ",
        " Intel(R) Gigabit 4P I350-t rNDC ",
        " NIC1 ",
        " 2 ",
        " 1000000000 ",
        " {AD68A885-C33E-4E9E-AA6E-3650513F72B3}",
    ],
    [
        "PWEX02 ",
        " C4:B7:2C:2A:7C:43 ",
        " Intel(R) Ethernet 10G 2P X520 Adapter ",
        " SLOT 6 Port 2 MAPI ",
        " 2 ",
        "  ",
        " {4C88A19B-5EE4-44A6-ACBB-262131EE1560}",
    ],
    [
        "PWEX02 ",
        " 40:90:7C:1A:45:F8 ",
        " Intel(R) Ethernet 10G 2P X520 Adapter ",
        " SLOT 6 Port 1 DAG ",
        " 2 ",
        "  ",
        " {70F3DEC7-8347-4157-B066-95F5672F39BA}",
    ],
    [
        "PWEX02 ",
        " DC:03:0E:A4:F4:0A ",
        " Intel(R) Gigabit 4P I350-t rNDC #2 ",
        " NIC2 ",
        " 7 ",
        " 9223372036854775807 ",
        " {84E4243F-9832-4923-93FB-F0A48F88FB1C}",
    ],
    [
        "PWEX02 ",
        " 6F:97:0D:91:B1:EA ",
        " Intel(R) Gigabit 4P I350-t rNDC #3 ",
        " NIC3 ",
        " 7 ",
        " 9223372036854775807 ",
        " {5EF9E8A8-5A85-42E7-AE8A-E3E63558D571}",
    ],
    [
        "PWEX02 ",
        " E7:AD:77:C9:73:A6 ",
        " Intel(R) Gigabit 4P I350-t rNDC #4 ",
        " NIC4 ",
        " 7 ",
        " 9223372036854775807 ",
        " {D7FE624A-1554-41D6-BC35-7EDDE1D396C3}",
    ],
    [
        "PWEX02 ",
        " 5C:74:5B:97:33:7D ",
        " Intel(R) Ethernet 10G 2P X520 Adapter ",
        " SLOT 4 Port 1 MAPI ",
        " 2 ",
        "  ",
        " {9BD62095-22A8-49CA-BA8B-A7846C6B5FDB}",
    ],
    [
        "PWEX02 ",
        " 7C:33:82:DE:F6:3A ",
        " Intel(R) Ethernet 10G 2P X520 Adapter ",
        " SLOT 4 Port 2 DAG ",
        " 2 ",
        "  ",
        " {9C4971CB-95AA-4B01-B828-F61B339E4F19}",
    ],
    [
        "PWEX02 ",
        " 5C:74:5B:97:33:7D ",
        " Microsoft Network Adapter Multiplexor Driver ",
        " MAPI-NET ",
        " 2 ",
        " 10000000000 ",
        " {0143C2F2-BFF1-4839-8766-82C6EB3FC440}",
    ],
    [
        "PWEX02 ",
        " 40:90:7C:1A:45:F8 ",
        " Microsoft Network Adapter Multiplexor Driver #2 ",
        " DAG-NET ",
        " 2 ",
        " 10000000000 ",
        " {16377083-0A9A-456B-AB35-9A37E78B3FD4}",
    ],
]

EXPECTED_WINPERF_IF_WIN32_NETWORKADAPTER_OUTPUT_2: Sequence[AdditionalIfData] = [
    AdditionalIfData(
        name="Intel(R) Gigabit 4P I350-t rNDC",
        alias="NIC1",
        speed=1000000000,
        oper_status="1",
        oper_status_name="up",
        mac_address="C6:E0:D0:A9:38:87",
        guid="{AD68A885-C33E-4E9E-AA6E-3650513F72B3}",
    ),
    AdditionalIfData(
        name="Intel(R) Ethernet 10G 2P X520 Adapter",
        alias="SLOT 6 Port 2 MAPI",
        speed=0,
        oper_status="1",
        oper_status_name="up",
        mac_address="C4:B7:2C:2A:7C:43",
        guid="{4C88A19B-5EE4-44A6-ACBB-262131EE1560}",
    ),
    AdditionalIfData(
        name="Intel(R) Ethernet 10G 2P X520 Adapter",
        alias="SLOT 6 Port 1 DAG",
        speed=0,
        oper_status="1",
        oper_status_name="up",
        mac_address="40:90:7C:1A:45:F8",
        guid="{70F3DEC7-8347-4157-B066-95F5672F39BA}",
    ),
    AdditionalIfData(
        name="Intel(R) Gigabit 4P I350-t rNDC #2",
        alias="NIC2",
        speed=0,
        oper_status="7",
        oper_status_name="Media disconnected",
        mac_address="DC:03:0E:A4:F4:0A",
        guid="{84E4243F-9832-4923-93FB-F0A48F88FB1C}",
    ),
    AdditionalIfData(
        name="Intel(R) Gigabit 4P I350-t rNDC #3",
        alias="NIC3",
        speed=0,
        oper_status="7",
        oper_status_name="Media disconnected",
        mac_address="6F:97:0D:91:B1:EA",
        guid="{5EF9E8A8-5A85-42E7-AE8A-E3E63558D571}",
    ),
    AdditionalIfData(
        name="Intel(R) Gigabit 4P I350-t rNDC #4",
        alias="NIC4",
        speed=0,
        oper_status="7",
        oper_status_name="Media disconnected",
        mac_address="E7:AD:77:C9:73:A6",
        guid="{D7FE624A-1554-41D6-BC35-7EDDE1D396C3}",
    ),
    AdditionalIfData(
        name="Intel(R) Ethernet 10G 2P X520 Adapter",
        alias="SLOT 4 Port 1 MAPI",
        speed=0,
        oper_status="1",
        oper_status_name="up",
        mac_address="5C:74:5B:97:33:7D",
        guid="{9BD62095-22A8-49CA-BA8B-A7846C6B5FDB}",
    ),
    AdditionalIfData(
        name="Intel(R) Ethernet 10G 2P X520 Adapter",
        alias="SLOT 4 Port 2 DAG",
        speed=0,
        oper_status="1",
        oper_status_name="up",
        mac_address="7C:33:82:DE:F6:3A",
        guid="{9C4971CB-95AA-4B01-B828-F61B339E4F19}",
    ),
    AdditionalIfData(
        name="Microsoft Network Adapter Multiplexor Driver",
        alias="MAPI-NET",
        speed=10000000000,
        oper_status="1",
        oper_status_name="up",
        mac_address="5C:74:5B:97:33:7D",
        guid="{0143C2F2-BFF1-4839-8766-82C6EB3FC440}",
    ),
    AdditionalIfData(
        name="Microsoft Network Adapter Multiplexor Driver #2",
        alias="DAG-NET",
        speed=10000000000,
        oper_status="1",
        oper_status_name="up",
        mac_address="40:90:7C:1A:45:F8",
        guid="{16377083-0A9A-456B-AB35-9A37E78B3FD4}",
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
        "E1:43:6A:0F:D3:F4 ",
        "IBM USB Remote NDIS   Network Device        #2 ",
        "Local Area Connection 2 ",
        "2 ",
        "9728000 ",
        "{A447D54F-0E4B-40B3-9FBA-228F7DCE8FC7}",
    ],
    [
        "TBWAW-VEEAM01",
        "BE:7E:D4:52:D3:1A ",
        "Intel(R) I350 Gigabit Network Connection ",
        "Ethernet 3 ",
        "7 ",
        "9223372036854775807 ",
        "{1C656D16-F30D-4714-9A7E-B3D3F9AD52FA}",
    ],
    [
        "TBWAW-VEEAM01",
        "15:35:42:65:DB:0A ",
        "Intel(R) I350 Gigabit Network Connection #2 ",
        "Ethernet 4 ",
        "7 ",
        "9223372036854775807 ",
        "{F9C89525-0500-4A6B-95AC-95F66BDA739A}",
    ],
    [
        "TBWAW-VEEAM01",
        "01:73:7F:4A:47:91 ",
        "Intel(R) I350 Gigabit Network Connection #3 ",
        "Ethernet 5 ",
        "7 ",
        "9223372036854775807 ",
        "{A0D28181-6DF8-4A80-9837-D2933D013510}",
    ],
    [
        "TBWAW-VEEAM01",
        "A2:22:DD:FD:C8:F9 ",
        "Intel(R) I350 Gigabit Network Connection #4 ",
        "Ethernet 6 ",
        "7 ",
        "9223372036854775807 ",
        "{95CA2691-7AFA-4842-A769-F521FE6173B2}",
    ],
    [
        "TBWAW-VEEAM01",
        "21:77:22:AE:F8:B4 ",
        "QLogic 1/10GbE Server Adapter ",
        "Ethernet 2 ",
        "2 ",
        " ",
        "{2B232067-0EE5-41EE-B498-0CA2FE8715D0}",
    ],
    [
        "TBWAW-VEEAM01",
        "35:37:CF:44:20:A2 ",
        "QLogic 1/10GbE Server Adapter ",
        "Ethernet ",
        "1 ",
        " ",
        "{11477AB1-0A73-449C-8768-A17F47C02A1F}",
    ],
    [
        "TBWAW-VEEAM01",
        "21:77:22:AE:F8:B4 ",
        "Microsoft Network Adapter Multiplexor Driver ",
        "LAN ",
        "2 ",
        "20000000000 ",
        "{4FCE4C48-6217-465A-B807-B61499AE570C}",
    ],
]

EXPECTED_WINPERF_IF_WIN32_NETWORKADAPTER_OUTPUT_1: Sequence[AdditionalIfData] = [
    AdditionalIfData(
        name="IBM USB Remote NDIS Network Device #2",
        alias="Local Area Connection 2",
        speed=9728000,
        oper_status="1",
        oper_status_name="up",
        mac_address="E1:43:6A:0F:D3:F4",
        guid="{A447D54F-0E4B-40B3-9FBA-228F7DCE8FC7}",
    ),
    AdditionalIfData(
        name="Intel(R) I350 Gigabit Network Connection",
        alias="Ethernet 3",
        speed=0,
        oper_status="7",
        oper_status_name="Media disconnected",
        mac_address="BE:7E:D4:52:D3:1A",
        guid="{1C656D16-F30D-4714-9A7E-B3D3F9AD52FA}",
    ),
    AdditionalIfData(
        name="Intel(R) I350 Gigabit Network Connection #2",
        alias="Ethernet 4",
        speed=0,
        oper_status="7",
        oper_status_name="Media disconnected",
        mac_address="15:35:42:65:DB:0A",
        guid="{F9C89525-0500-4A6B-95AC-95F66BDA739A}",
    ),
    AdditionalIfData(
        name="Intel(R) I350 Gigabit Network Connection #3",
        alias="Ethernet 5",
        speed=0,
        oper_status="7",
        oper_status_name="Media disconnected",
        mac_address="01:73:7F:4A:47:91",
        guid="{A0D28181-6DF8-4A80-9837-D2933D013510}",
    ),
    AdditionalIfData(
        name="Intel(R) I350 Gigabit Network Connection #4",
        alias="Ethernet 6",
        speed=0,
        oper_status="7",
        oper_status_name="Media disconnected",
        mac_address="A2:22:DD:FD:C8:F9",
        guid="{95CA2691-7AFA-4842-A769-F521FE6173B2}",
    ),
    AdditionalIfData(
        name="QLogic 1/10GbE Server Adapter",
        alias="Ethernet 2",
        speed=0,
        oper_status="1",
        oper_status_name="up",
        mac_address="21:77:22:AE:F8:B4",
        guid="{2B232067-0EE5-41EE-B498-0CA2FE8715D0}",
    ),
    AdditionalIfData(
        name="QLogic 1/10GbE Server Adapter",
        alias="Ethernet",
        speed=0,
        oper_status="2",
        oper_status_name="Connecting",
        mac_address="35:37:CF:44:20:A2",
        guid="{11477AB1-0A73-449C-8768-A17F47C02A1F}",
    ),
    AdditionalIfData(
        name="Microsoft Network Adapter Multiplexor Driver",
        alias="LAN",
        speed=20000000000,
        oper_status="1",
        oper_status_name="up",
        mac_address="21:77:22:AE:F8:B4",
        guid="{4FCE4C48-6217-465A-B807-B61499AE570C}",
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
                            (Names.ISATAP_A4, 100000),
                            (Names.ISATAP_4F, 100000),
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
                            (Names.NIN, 100000),
                            (Names.ISATAP_01, 100000),
                            (Names.ISATAP_16, 100000),
                            (Names.ISATAP_7A, 100000),
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
                    "40:90:7C:1A:45:F8;7C:33:82:DE:F6:3A",
                    "SLOT 6 Port 1 DAG;SLOT 4 Port 2 DAG",
                    "Intel(R) Ethernet 10G 2P X520 Adapter     #2;Intel(R) Ethernet 10G 2P X520 Adapter   #4",
                    "10000000000;10000000000",
                    "{70F3DEC7-8347-4157-B066-95F5672F39BA};{9C4971CB-95AA-4B01-B828-F61B339E4F19}",
                ],
                [
                    "MAPI-NET ",
                    "SwitchIndependent ",
                    "Dynamic ",
                    "C4:B7:2C:2A:7C:43;5C:74:5B:97:33:7D",
                    "SLOT 6 Port 2 MAPI;SLOT 4 Port 1 MAPI",
                    "Intel(R) Ethernet 10G 2P X520 Adapter;Intel(R) Ethernet 10G 2P X520 Adapter #3",
                    "10000000000;10000000000",
                    "{4C88A19B-5EE4-44A6-ACBB-262131EE1560};{9BD62095-22A8-49CA-BA8B-A7846C6B5FDB}",
                ],
            ],
            {
                "{70F3DEC7-8347-4157-B066-95F5672F39BA}": TeamingData(
                    team_name="DAG-NET",
                    name="Intel(R) Ethernet 10G 2P X520 Adapter #2",
                ),
                "{9C4971CB-95AA-4B01-B828-F61B339E4F19}": TeamingData(
                    team_name="DAG-NET",
                    name="Intel(R) Ethernet 10G 2P X520 Adapter #4",
                ),
                "{4C88A19B-5EE4-44A6-ACBB-262131EE1560}": TeamingData(
                    team_name="MAPI-NET",
                    name="Intel(R) Ethernet 10G 2P X520 Adapter",
                ),
                "{9BD62095-22A8-49CA-BA8B-A7846C6B5FDB}": TeamingData(
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
                    "14:42:AD:DB:92:BB;5B:02:F6:E1:43:36",
                    "Ethernet 3;Ethernet 6",
                    "HP NC523SFP 10Gb 2-port Server Adapter;HP NC523SFP 10Gb 2-port Server Adapter #3",
                    "10000000000;10000000000",
                    "{9F992251-4863-4207-9B48-FA095C0A1165};{F6036562-3810-402C-BE91-5B78E0C94AA0}",
                ],
                [
                    "SRVMWTeam ",
                    "Lacp ",
                    "Dynamic ",
                    "E9:A8:BE:9B:83:23;99:CC:82:AB:97:98",
                    "Ethernet 7;Ethernet 5",
                    "HP NC382i DP Multifunction Gigabit Server Adapter #52;HP NC382i DP Multifunction Gigabit Server Adapter #53",
                    "1000000000;1000000000",
                    "{7A548B9E-C618-4620-B0BC-1974251252DB};{B434E38A-A0A7-4CBD-959D-FB450768C511}",
                ],
            ],
            {
                "{9F992251-4863-4207-9B48-FA095C0A1165}": TeamingData(
                    team_name="PVSMWTeam",
                    name="HP NC523SFP 10Gb 2-port Server Adapter",
                ),
                "{F6036562-3810-402C-BE91-5B78E0C94AA0}": TeamingData(
                    team_name="PVSMWTeam",
                    name="HP NC523SFP 10Gb 2-port Server Adapter #3",
                ),
                "{7A548B9E-C618-4620-B0BC-1974251252DB}": TeamingData(
                    team_name="SRVMWTeam",
                    name="HP NC382i DP Multifunction Gigabit Server Adapter #52",
                ),
                "{B434E38A-A0A7-4CBD-959D-FB450768C511}": TeamingData(
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
                    "35:37:CF:44:20:A2;21:77:22:AE:F8:B4",
                    "Ethernet;Ethernet 2",
                    "QLogic 1/10GbE Server Adapter #2;QLogic 1/10GbE Server Adapter",
                    "10000000000;10000000000",
                    "{11477AB1-0A73-449C-8768-A17F47C02A1F};{2B232067-0EE5-41EE-B498-0CA2FE8715D0}",
                ],
            ],
            {
                "{11477AB1-0A73-449C-8768-A17F47C02A1F}": TeamingData(
                    team_name="LAN",
                    name="QLogic 1/10GbE Server Adapter #2",
                ),
                "{2B232067-0EE5-41EE-B498-0CA2FE8715D0}": TeamingData(
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
                ["Z3127130", "13:09:72:66:8A:B3", "Broadcom OK 1", "NIC2", "2"],
                ["Z3127130", "", "Broadcom XX Skip", "NIC4", "4"],
                ["Z3127130", "54:8B:A4:39:61:53", "Broadcom OK 2", "NIC1", "2"],
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
                    mac_address="13:09:72:66:8A:B3",
                    guid=None,
                ),
                AdditionalIfData(
                    name="Broadcom OK 2",
                    alias="NIC1",
                    speed=0,
                    oper_status="1",
                    oper_status_name="up",
                    mac_address="54:8B:A4:39:61:53",
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
                "{FD85A0EF-1969-462E-87AE-6C78F8CE4216}",
            ],
            [
                "Intel(R) PRO/1000 MT Desktop Adapter_",
                "Ethernet",
                "999",
                "1",
                "Up",
                "39-86-7E-CE-71-1F",
                "{4AA86136-917B-45D2-BE98-087B589B8CA0}",
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
            guid="{FD85A0EF-1969-462E-87AE-6C78F8CE4216}",
        ),
        AdditionalIfData(
            name="Intel(R) PRO/1000 MT Desktop Adapter",
            alias="Ethernet",
            speed=999,
            oper_status="1",
            oper_status_name="Up",
            mac_address="39:86:7E:CE:71:1F",
            guid="{4AA86136-917B-45D2-BE98-087B589B8CA0}",
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
                Names.ISATAP_A4: _entry(8, Names.ISATAP_A4, 100000),
                Names.ISATAP_4F: _entry(9, Names.ISATAP_4F, 100000),
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
                    phys_address='!w"®ø´',
                ),
                _entry(
                    3,
                    Names.INTEL_I350,
                    0,
                    Mode.DISCONN,
                    alias="Ethernet 3",
                    phys_address="¾~ÔRÓ\x1a",
                ),
                _entry(
                    4,
                    Names.INTEL_I350_2,
                    0,
                    Mode.DISCONN,
                    alias="Ethernet 4",
                    phys_address="\x155BeÛ\n",
                ),
                _entry(
                    5,
                    Names.INTEL_I350_3,
                    0,
                    Mode.DISCONN,
                    alias="Ethernet 5",
                    phys_address="\x01s\x7fJG\x91",
                ),
                _entry(
                    6,
                    Names.INTEL_I350_4,
                    0,
                    Mode.DISCONN,
                    alias="Ethernet 6",
                    phys_address='¢"ÝýÈù',
                ),
                _entry(
                    7,
                    Names.IBM_USB_2,
                    9728000,
                    Mode.UP,
                    alias="Local Area Connection 2",
                    phys_address="áCj\x0fÓô",
                ),
                _entry(8, Names.ISATAP_A4, 100000),
                _entry(9, Names.ISATAP_4F, 100000),
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
                Names.NIN: _entry(9, Names.NIN, 100000),
                Names.ISATAP_01: _entry(10, Names.ISATAP_01, 100000),
                Names.ISATAP_16: _entry(11, Names.ISATAP_16, 100000),
                Names.ISATAP_7A: _entry(12, Names.ISATAP_7A, 100000),
            },
            {
                "{70F3DEC7-8347-4157-B066-95F5672F39BA}": TeamingData(
                    team_name="DAG-NET",
                    name="Intel(R) Ethernet 10G 2P X520 Adapter #2",
                ),
                "{9C4971CB-95AA-4B01-B828-F61B339E4F19}": TeamingData(
                    team_name="DAG-NET",
                    name="Intel(R) Ethernet 10G 2P X520 Adapter #4",
                ),
                "{4C88A19B-5EE4-44A6-ACBB-262131EE1560}": TeamingData(
                    team_name="MAPI-NET",
                    name="Intel(R) Ethernet 10G 2P X520 Adapter",
                ),
                "{9BD62095-22A8-49CA-BA8B-A7846C6B5FDB}": TeamingData(
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
                    phys_address="ÆàÐ©8\x87",
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
                        phys_address="Ä·,*|C",
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
                        phys_address="@\x90|\x1aEø",
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
                    phys_address="Ü\x03\x0e¤ô\n",
                ),
                _entry(
                    5,
                    Names.INTEL_NDC_3,
                    0,
                    mode=Mode.DISCONN,
                    alias="NIC3",
                    phys_address="o\x97\r\x91±ê",
                ),
                _entry(
                    6,
                    Names.INTEL_NDC_4,
                    0,
                    mode=Mode.DISCONN,
                    alias="NIC4",
                    phys_address="ç\xadwÉs¦",
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
                        phys_address="\\t[\x973}",
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
                        phys_address="|3\x82Þö:",
                        oper_status_name="up",
                        speed_as_text="",
                        group="DAG-NET",
                        node=None,
                        admin_status=None,
                    ),
                    _counters[Names.INTEL_X520_4],
                ),
                _entry(9, Names.NIN, 100000),
                _entry(10, Names.ISATAP_01, 100000),
                _entry(11, Names.ISATAP_16, 100000),
                _entry(12, Names.ISATAP_7A, 100000),
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
    assert sort_inventory_result(
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
                        phys_address="\\óü7*0",
                    ),
                    Names.INTEL_I350: _entry(
                        3,
                        Names.INTEL_I350,
                        0,
                        Mode.DISCONN,
                        alias="Ethernet 3",
                        phys_address="@òé!¾Ò",
                    ),
                    Names.INTEL_I350_2: _entry(
                        4,
                        Names.INTEL_I350_2,
                        0,
                        Mode.DISCONN,
                        alias="Ethernet 4",
                        phys_address="@òé!¾Ó",
                    ),
                    Names.IBM_USB_2: _entry(
                        7,
                        Names.IBM_USB_2,
                        9728000,
                        Mode.UP,
                        alias="Local Area Connection 2",
                        phys_address="Bòé!¾Ñ",
                    ),
                    Names.ISATAP_A4: _entry(8, Names.ISATAP_A4, 100000),
                },
                found_windows_if=False,
                found_mk_dhcp_enabled=False,
            ),
            None,
            None,
        )
    ) == sort_inventory_result(
        [
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
                    "phys_address": "5C:F3:FC:37:2A:30",
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
                    "phys_address": "42:F2:E9:21:BE:D1",
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
                    "description": "isatap.{A447D54F-0E4B-40B3-9FBA-228F7DCE8FC7}",
                    "alias": "isatap.{A447D54F-0E4B-40B3-9FBA-228F7DCE8FC7}",
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
    )
