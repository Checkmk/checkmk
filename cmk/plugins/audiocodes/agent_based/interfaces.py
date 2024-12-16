#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    InventoryPlugin,
    InventoryResult,
    OIDEnd,
    SNMPSection,
    SNMPTree,
    StringTable,
    TableRow,
)

from .lib import DETECT_AUDIOCODES

STATUS_CODE_TO_HUMAN_READABLE = {
    "1": "active",
    "2": "notInService",
    "3": "notReady",
}
SIP_INTERFACE_APPLICATION_TYPE_TO_HUMAN_READABLE = {
    "0": "gwIP2IP",
    "1": "sas",
    "2": "sbc",
}
SYS_INTERFACE_APPLICATION_TYPE_TO_HUMAN_READABLE = {
    "0": "oam",
    "1": "media",
    "2": "control",
    "3": "oamAndMedia",
    "4": "oamAndControl",
    "5": "mediaAndControl",
    "6": "oamAndMediaAndControl",
    "99": "maintenance",
}
SYS_INTERFACE_MODE_TO_HUMAN_READABLE = {
    "3": "IPv6PrefixManual",
    "4": "IPv6Manual",
    "10": "IPv4Manual",
}


@dataclass(frozen=True, kw_only=True)
class Device:
    rowstatus: str
    vlan: str
    name: str


@dataclass(kw_only=True)
class SysInterface:
    rowstatus: str
    apptype: str
    mode: str
    ip: str
    gateway: str
    vlan: str
    name: str
    device: Device | None = None


@dataclass(frozen=True, kw_only=True)
class SIPInterface:
    index: str
    rowstatus: str
    apptype: str
    udpport: int
    tcpport: int
    tlsport: int
    name: str


@dataclass(frozen=True, kw_only=True)
class Interface:
    sip: SIPInterface
    sys: SysInterface | None


def parse_audiocodes_interfaces(
    string_table: Sequence[StringTable],
) -> Sequence[Interface]:
    if not string_table:
        return []

    sys_interface_info_by_index = _create_sys_interface_by_index(string_table[1], string_table[2])

    return [
        Interface(
            sip=_create_sip_interface(line),
            sys=sys_interface_info_by_index.get(_extract_sys_interface_index(line[4])),
        )
        for line in string_table[0]
    ]


def _extract_sys_interface_index(sip_interface_network_interface: str) -> str:
    return (
        sip_interface_network_interface[43:]
        if sip_interface_network_interface.startswith(".1.3.6.1.4.1.5003.9.10.10.1.3.1.30.22.1.11.")
        else ""
    )


def _create_sip_interface(line: Sequence[str]) -> SIPInterface:
    return SIPInterface(
        index=line[0],
        rowstatus=STATUS_CODE_TO_HUMAN_READABLE[line[1]],
        apptype=SIP_INTERFACE_APPLICATION_TYPE_TO_HUMAN_READABLE[line[5]],
        udpport=int(line[6]),
        tcpport=int(line[7]),
        tlsport=int(line[8]),
        name=line[10],
    )


def _create_sys_interface_by_index(
    sys_string_table: StringTable,
    device_string_table: StringTable,
) -> Mapping[str, SysInterface]:
    if not sys_string_table:
        return {}

    device_by_index = _create_device_by_index(device_string_table)

    return {
        line[0]: SysInterface(
            rowstatus=STATUS_CODE_TO_HUMAN_READABLE[line[1]],
            apptype=SYS_INTERFACE_APPLICATION_TYPE_TO_HUMAN_READABLE[line[2]],
            mode=SYS_INTERFACE_MODE_TO_HUMAN_READABLE[line[3]],
            ip=f"{line[4]}/{line[5]}",
            gateway=line[6],
            vlan=line[7],
            name=line[8],
            device=device_by_index.get(_extract_device_index(line[12])),
        )
        for line in sys_string_table
    }


def _extract_device_index(sys_interface_underlying_device: str) -> str:
    return (
        sys_interface_underlying_device[42:]
        if sys_interface_underlying_device.startswith(".1.3.6.1.4.1.5003.9.10.10.1.3.1.30.26.1.7.")
        else ""
    )


def _create_device_by_index(
    device_string_table: StringTable,
) -> Mapping[str, Device]:
    return {
        line[0]: Device(
            rowstatus=STATUS_CODE_TO_HUMAN_READABLE[line[1]],
            vlan=line[2],
            name=line[3],
        )
        for line in device_string_table
    }


snmp_section_audiocodes_sip_interfaces = SNMPSection(
    name="audiocodes_sip_interfaces",
    detect=DETECT_AUDIOCODES,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.5003.9.10.3.1.1.27.21.1",
            oids=[
                "1",  # 0  AcGateway::sipInterfaceIndex
                "2",  # 1  AcGateway::sipInterfaceRowStatus
                "3",  # 2  AcGateway::sipInterfaceAction
                "4",  # 3  AcGateway::sipInterfaceActionResult
                "5",  # 4  AcGateway::sipInterfaceNetworkInterface
                "6",  # 5  AcGateway::sipInterfaceApplicationType
                "7",  # 6  AcGateway::sipInterfaceUDPPort
                "8",  # 7  AcGateway::sipInterfaceTCPPort
                "9",  # 8  AcGateway::sipInterfaceTLSPort
                "10",  # 9  AcGateway::sipInterfaceSRD
                "11",  # 10 AcGateway::sipInterfaceInterfaceName
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.5003.9.10.10.1.3.1.30.22.1",
            oids=[
                OIDEnd(),
                "2",  # 1  AC-SYSTEM-MIB::acSysInterfaceRowStatus
                "5",  # 2  AC-SYSTEM-MIB::acSysInterfaceApplicationTypes
                "6",  # 3  AC-SYSTEM-MIB::acSysInterfaceMode
                "7",  # 4  AC-SYSTEM-MIB::acSysInterfaceIPAddress
                "8",  # 5  AC-SYSTEM-MIB::acSysInterfacePrefixLength
                "9",  # 6  AC-SYSTEM-MIB::acSysInterfaceGateway
                "10",  # 7  AC-SYSTEM-MIB::acSysInterfaceVlanID
                "11",  # 8  AC-SYSTEM-MIB::acSysInterfaceName
                "12",  # 9  AC-SYSTEM-MIB::acSysInterfacePrimaryDNSServerIPAddress
                "13",  # 10 AC-SYSTEM-MIB::acSysInterfaceSecondaryDNSServerIPAddress
                "14",  # 11 AC-SYSTEM-MIB::acSysInterfaceUnderlyingInterface
                "15",  # 12 AC-SYSTEM-MIB::acSysInterfaceUnderlyingDevice
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.5003.9.10.10.1.3.1.30.26.1",
            oids=[
                OIDEnd(),
                "2",  # 1  AC-SYSTEM-MIB::acSysEthernetDeviceRowStatus
                "5",  # 2  AC-SYSTEM-MIB::acSysEthernetDeviceVlanID
                "7",  # 3  AC-SYSTEM-MIB::acSysEthernetDeviceName
            ],
        ),
    ],
    parse_function=parse_audiocodes_interfaces,
)


def inventory_audiocodes_sip_interfaces(section: Sequence[Interface]) -> InventoryResult:
    for interface in section:
        yield TableRow(
            path=["networking", "sip_interfaces"],
            key_columns={"index": interface.sip.index, "name": interface.sip.name},
            inventory_columns={
                "application_type": interface.sip.apptype,
                "sys_interface": interface.sys.name if interface.sys else None,
                "device": interface.sys.device.name
                if interface.sys and interface.sys.device
                else None,
                "tcp_port": interface.sip.tcpport,
                "gateway": interface.sys.gateway if interface.sys else None,
            },
        )


inventory_plugin_audiocodes_sip_interfaces = InventoryPlugin(
    name="audiocodes_sip_interfaces",
    inventory_function=inventory_audiocodes_sip_interfaces,
)
