#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2023-12-27
# File  : inv_ip_addresses.py
#
# inventory of IPv4 address information
#
# 2024-04-07: fixed missing/wrong netmask (ThX bitwiz@forum.checkmk.com)
#             improved validation of SNMP input data
#             drop this host ip address (0.0.0.0)
# 2024-12-02: incompatible: changed host label to nvdct/l3v4_host:yes and nvdct/l3v4_routing:yes
# 2024-12-03: added IP-MIB::ipAddressTable for IPv6 support
#             incompatible: renamed to inv_ip_address -> remove inv_ipv4_address.mkp before updating
# 2024-12-05  changed to use ip_interface
# 2024-12-06: incompatible: changed host label to nvdct/l3v4_topology:host and nvdct/l3v4_topology:router
# 2024-12-09: rewritten for CMK checkAPI 2.0
# 2024-12-10: fixed crash in host label function (AttributeError ('dict_values' object has no attribute 'version'))
#             added support for ipv6z address type
#             fixed duplicate ip information in section
#             added host label nvdct/l3v6_topology:host and nvdct/l3v6_topology:router
# 2024-12-14: fixed crash if raw_address is longer than raw_length (fortinet_2), ends with interface index
#             better handling of raw_address length
#             fixed crash in IBM raw_address format (dec_ip_address index out of range)
# 2025-01-21: added drop broadcast IPs
# 2025-01-24: fixed crash on bad prefix-length (to long for the ip version i.e. 33 for ipv4) ThX to to andreas doehler
# 2025-10-28: fixed crash in ip_info_20 on empty values (ThX to Jan Rzaczek)

from collections.abc import Mapping, MutableSequence, Sequence
from ipaddress import AddressValueError, NetmaskValueError, ip_interface
from re import match as re_match
from typing import List

from cmk.agent_based.v2 import (
    HostLabel,
    HostLabelGenerator,
    InventoryPlugin,
    InventoryResult,
    OIDBytes,
    OIDEnd,
    SNMPSection,
    SNMPTree,
    StringByteTable,
    TableRow,
    exists,
)


__ip_info_34_ios = [
    [
        '1.4.10.10.10.230',  # OID end -> type: ipv4, length: 4, ipv4 address
        [],  # ip address -> empty
        '3',  # interface index
        '.1.3.6.1.2.1.4.32.1.5.3.1.4.10.10.10.228.30'  # prefix -> last number (30)
    ],
    [
        '2.16.42.0.28.160.16.0.1.53.0.0.0.0.0.0.0.2',  # OID end -> type: ipv6, length: 16, ipv6 address
        [],
        '3',
        '.1.3.6.1.2.1.4.32.1.5.3.2.16.42.0.28.160.16.0.1.53.0.0.0.0.0.0.0.0.64'
    ],
    [
        '4.20.254.128.0.0.0.0.0.0.114.219.152.255.254.159.41.2.18.0.0.8',
        # OID end -> type: ipv6z, length: 20, ipv6 address with interface identifier (18.0.0.8)
        [],
        '3',
        '.0.0'
    ],
]
__ip_info_34_ibm = [
    [
        '1.15.48.49.48.46.49.52.48.46.49.54.48.46.48.49.55',
        # OID end -> type: ipv4, length: 15, ipv4 address ('010.140.160.017')
        [],
        '805306370',
        '.0.0'
    ],
    [
        '2.39.48.48.48.48.58.48.48.48.48.58.48.48.48.48.58.48.48.48.48.58.48.48.48.48.58.48.48.48.48.58.48.48.48.48.58.48.48.48.49',
        # OID end -> type: ipv6, length: 39, ipv6 address ('0000:0000:0000:0000:0000:0000:0000:0001')
        [],
        '805306371',
        '.0.0'
    ],
]
__ip_info_34_firepower = [
    [
        '1.10.1.1.2',  # OID end -> type: ipv4, , ipv4 address ('10.1.1.2')
        [10, 1, 1, 2],  # ip address in dec bytes
        '18',
        '.1.3.6.1.2.1.4.32.1.5.18.1.10.1.1.0.24'
    ],
    [
        '2.253.0.0.0.0.0.0.1.0.0.0.0.0.0.0.1',
        # OID end -> type: ipv6, ipv6 address ('253.0.0.0.0.0.0.1.0.0.0.0.0.0.0.1')
        [253, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1],  # ip address in dec bytes
        '4',
        '.1.3.6.1.2.1.4.32.1.5.4.2.253.0.0.0.0.0.0.1.0.0.0.0.0.0.0.0.64'
    ],
]
__ip_info_34_fortinet = [
    [
        '1.10.118.132.1.76',  # OID end -> type: ipv4, ipv4 address (10.118.132.1), interface index (76)
        [],
        '76',
        '.0.0.0'  # prefix -> missing
    ],
    [
        '2.10762.22982.8208.4113.0.0.0.282.40',
        # OID end -> type: ipv6, ipv6 address (10762.22982.8208.4113.0.0.0.282), interface index (76)
        [],
        '40',
        '.0.0.0'  # prefix -> missing
    ],
]
__ip_info_34_fortinet_2 = [
    ['1.4.10.86.60.1.16', [], '16', '.1.3.6.1.2.1.4.32.1.5.16.1.10.86.60.0.27'],
    ['2.16.254.128.0.0.0.0.0.0.2.0.94.254.81.92.98.50.20', [], '20', '.1.3.6.1.2.1.4.32.1.5.20.2.254.128.0.0.0.0.0.0.0.0.0.0.0.0.0.0.64'],
]

Section = Sequence[Mapping[str, ip_interface]] | None


def parse_inv_ip_addresses(string_table: List[StringByteTable]) -> Section:
    try:
        ip_info_20, ip_info_34, if_info = string_table
    except ValueError:
        return

    try:
        interface_by_index = {if_index: if_name for if_index, if_name in if_info}
    except ValueError:
        interface_by_index = {}

    ip_infos: MutableSequence[Mapping[str, ip_interface]] = []

    for entry in ip_info_34:
        try:
            oid_end, dec_ip_address, if_index, ip_prefix = entry
        except ValueError:
            continue

        if oid_end.startswith('4.20.254.128.'):  # ipv6z, link local
            ip_prefix = '64'

        if (prefix := ip_prefix.split('.')[-1]) == '0':  # drop entries without prefix (0) -> fortinet
            continue

        if not (raw_ip := re_match(r'(\d+)\.(\d+)\.([\d|\.]+)', oid_end)):
            continue

        raw_type, raw_length, raw_address = raw_ip.groups()

        if dec_ip_address:
            raw_address = '.'.join(str(x) for x in dec_ip_address)
            raw_length = str(len(dec_ip_address))

        match raw_type:
            case '1':  # IPv4 address
                if raw_length == '4':
                    raw_address = '.'.join(x for x in raw_address.split('.')[0:4])
                if raw_length == '15':
                    raw_address = ''.join([chr(int(x)) for x in raw_address.split('.')])
                    raw_address = '.'.join([str(int(x)) for x in raw_address.split('.')])
            case '2':  # IPv6 address
                match raw_length:
                    case '16':
                        raw_address = [f'{int(x):02x}' for x in raw_address.split('.')[0:16]]
                        raw_address = ':'.join(
                            [''.join([raw_address[i], raw_address[i + 1]]) for i in range(0, 16, 2)]
                        )
                    case '39':
                        raw_address = ''.join([chr(int(x)) for x in raw_address.split('.')])
            case '4':  # ipv6z
                # [
                #     ['4.20.254.128.0.0.0.0.0.0.1.146.1.104.0.16.1.65.18.0.0.2', [], '1', '.0.0'],
                #     ['4.20.254.128.0.0.0.0.0.0.1.146.1.104.0.16.1.65.18.0.0.3', [], '2', '.0.0']
                # ]
                # IP-MIB::ipAddressIfIndex.ipv6z."fe:80:00:00:00:00:00:00:01:92:01:68:00:10:01:41%301989890" = INTEGER: 1
                # IP-MIB::ipAddressIfIndex.ipv6z."fe:80:00:00:00:00:00:00:01:92:01:68:00:10:01:41%301989891" = INTEGER: 2
                match raw_length:
                    case '20':
                        raw_address = [f'{int(x):02x}' for x in raw_address.split('.')]
                        scope_id = '.'.join(raw_address[16:])
                        raw_address = ':'.join(
                            [''.join([raw_address[i], raw_address[i + 1]]) for i in range(0, 16, 2)]
                        )
                        raw_address += f'%{scope_id}'
            case _:
                continue

        try:
            interface_ip = ip_interface(f'{raw_address}/{prefix}')
        except (AddressValueError, NetmaskValueError, ValueError):
            continue

        if interface_ip.ip.compressed == interface_ip.network.broadcast_address.compressed:
            continue  # drop broadcast IPs

        if interface_ip.ip.is_loopback:  # Drop localhost
            continue

        if interface_ip.ip.exploded == '0.0.0.0':  # drop this host address
            continue

        ip_infos.append({(str(interface_by_index.get(if_index, if_index))): interface_ip})

    for entry in ip_info_20:
        try:
            raw_address, if_index, raw_netmask = entry
        except ValueError:
            continue

        try:
            interface_ip = ip_interface(f'{raw_address}/{raw_netmask}')
        except (AddressValueError, NetmaskValueError, ValueError):
            continue

        if interface_ip.ip.is_loopback:  # Drop localhost
            continue

        if interface_ip.ip.exploded == '0.0.0.0':  # drop this host address
            continue

        if not (ip_info := {str(interface_by_index.get(if_index, if_index)): interface_ip}) in ip_infos:
            ip_infos.append(ip_info)

    return ip_infos


def host_label_inv_ip_addresses(section: Section) -> HostLabelGenerator:
    """
    Host label function
    Labels:
        nvdct/l3v4_topology:
            "host" is set for all devices with one IPv4 address
            "router" is set for all devices with more than one IPv4 address.
        nvdct/l3v6_topology:
            "host" is set for all devices with one IPv6 address
            "router" is set for all devices with more than one IPv6 address.

        Link-local ("FE80::/64), unspecified ("::") and local-host ("127.0.0.0/8", "::1") IPs don't count.
    """

    valid_v4_ips = 0
    valid_v6_ips = 0
    for interface_ips in section:
        for interface_ip in interface_ips.values():
            if interface_ip.version == 4 and not interface_ip.is_loopback:
                valid_v4_ips += 1
                if valid_v4_ips == 1:
                    yield HostLabel(name="nvdct/l3v4_topology", value="host")
                if valid_v4_ips == 2:
                    yield HostLabel(name="nvdct/l3v4_topology", value="router")

            elif interface_ip.version == 6 and not interface_ip.is_loopback \
                    and not interface_ip.is_link_local and not interface_ip.is_unspecified:
                valid_v6_ips += 1
                if valid_v6_ips == 1:
                    yield HostLabel(name="nvdct/l3v6_topology", value="host")
                if valid_v6_ips == 2:
                    yield HostLabel(name="nvdct/l3v6_topology", value="router")


def inventory_ip_addresses(section: Section) -> InventoryResult:
    address_type = {
        4: 'ipv4',
        6: 'ipv6',
    }
    for entry in section:
        for if_name, ip_data in entry.items():
            try:  # ipv4 has no scope_id
                scope_id = ip_data.scope_id
            except AttributeError:
                scope_id = None

            yield TableRow(
                path=['networking', 'addresses'],
                key_columns={
                    'address': str(ip_data.ip.compressed),
                    'device': if_name,
                },
                inventory_columns={
                    'broadcast': str(ip_data.network.broadcast_address),
                    'cidr': ip_data.network.prefixlen,
                    'netmask': str(ip_data.network.netmask),
                    'network': str(ip_data.network.network_address),
                    'type': address_type.get(ip_data.version).lower(),
                    **({"scope_id": str(scope_id)} if scope_id else {}),
                }
            )


snmp_section_inv_ip_address = SNMPSection(
    name='inv_ip_addresses',
    parse_function=parse_inv_ip_addresses,
    host_label_function=host_label_inv_ip_addresses,
    fetch=[
        SNMPTree(
            base='.1.3.6.1.2.1.4.20.1',  # IP-MIB::ipAddrEntry
            oids=[
                '1',  # ipAdEntAddr
                '2',  # ipAdEntIfIndex
                '3',  # ipAdEntNetMask
            ]
        ),
        SNMPTree(
            base='.1.3.6.1.2.1.4.34.1',  # IP-MIB::ipAddrEntry
            oids=[
                OIDEnd(),  # type.length.ip-address
                OIDBytes('2'),  # ipAddressAddr
                '3',  # ipAddressIfIndex
                '5',  # ipAddressPrefix
            ]
        ),
        SNMPTree(
            base='.1.3.6.1.2.1.31.1.1.1',  #
            oids=[
                OIDEnd(),  # ifIndex
                '1',  # ifName
            ]),
    ],
    detect=exists('.1.3.6.1.2.1.4.20.1.1.*'),  #
)

inventory_plugin_inv_ip_address = InventoryPlugin(
    name='inv_ip_addresses',
    inventory_function=inventory_ip_addresses,
)

