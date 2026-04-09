#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

from collections.abc import Iterable, Sequence

from cmk.agent_based.v2 import (
    exists,
    HostLabelGenerator,
    InventoryPlugin,
    InventoryResult,
    OIDBytes,
    OIDEnd,
    SNMPSection,
    SNMPTree,
    StringByteTable,
)
from cmk.plugins.lib.host_labels_interfaces import host_labels_if
from cmk.plugins.lib.interfaces import (
    AugmentedIPInterface,
    AugmentedIPv4Interface,
    AugmentedIPv6Interface,
    IPNetworkAdapter,
)
from cmk.plugins.lib.inventory_interfaces import inventorize_ip_addresses

Section = Iterable[IPNetworkAdapter]


def address_str_from(adr_type: int, adr_length: int, raw_address: Sequence[int]) -> None | str:
    """Returns an address string from 'raw' data encoded in OID suffixes. Addresses
    can be both IPv4 and IPv6 with or without a 'scope_id' (IPv6z). IPv4 and IPv6
    can be represented as a list of integers (as you would expect it) or as a
    sequence of bytes encoding a valid address string.
    >>> address_str_from(1, 4, [10, 86, 60, 1, 16])
    '10.86.60.1'
    >>> address_str_from(1, 15, [48, 49, 48, 46, 49, 52, 48, 46, 49, 54, 48, 46, 48, 49, 55])
    '10.140.160.17'
    >>> address_str_from(2, 16, [254, 128, 0, 0, 0, 0, 0, 0, 2, 0, 94, 254, 81, 92, 98, 50, 20])
    'fe80:0000:0000:0000:0200:5efe:515c:6232'
    >>> address_str_from(2, 39, [48, 48, 48, 48, 58, 48, 48, 48, 48, 58,
    ...                          48, 48, 48, 48, 58, 48, 48, 48, 48, 58,
    ...                          48, 48, 48, 48, 58, 48, 48, 48, 48, 58,
    ...                          48, 48, 48, 48, 58, 48, 48, 48, 49])
    '0000:0000:0000:0000:0000:0000:0000:0001'
    >>> address_str_from(4, 20, [254, 128, 0, 0, 0, 0, 0, 0, 114, 219, 152, 255, 254, 159, 41, 2, 18, 0, 0, 8])
    'fe80:0000:0000:0000:72db:98ff:fe9f:2902%12.00.00.08'
    """
    match (adr_type, adr_length):
        # IPv4 address - direct decimal representation
        case (1, 4):
            # strip potential extra elements
            return ".".join(map(str, raw_address[0:4]))
        # IPv4 address - ascii representation
        case (1, 15):
            # same as bytes(raw_address).decode() but removes leading zeros
            return ".".join(map(str, map(int, bytes(raw_address).split(b"."))))
        # IPv6 address - decimal representation
        case (2, 16):
            hex_str = "".join(f"{c:02x}" for c in raw_address)
            return ":".join(hex_str[i : i + 4] for i in range(0, 32, 4))
        # IPv6 address - ascii representation
        case (2, 39):
            return bytes(raw_address).decode()
        # IPv6z - like IPv6 decimal but with scope_id starting from index=16
        case (4, 20):
            hex_str = "".join(f"{c:02x}" for c in raw_address)
            ipv4_adr = ":".join(hex_str[i : i + 4] for i in range(0, 32, 4))
            scope_id = ".".join(hex_str[i : i + 2] for i in range(32, len(hex_str), 2))
            return f"{ipv4_adr}%{scope_id}"
        # cases (1, 10) | (1, 151) | (1, 192) | (3, 8) | (2, 110) | (4, 16) are not supported
        # yet but might be in the future
        case _:
            return None


def ip_info_34_from(
    entry: Sequence[str | Sequence[int]],
) -> None | tuple[str, AugmentedIPv4Interface | AugmentedIPv6Interface]:
    """
    >>> ip_info_34_from(
    ...     ['1.4.10.86.60.1.16', [], '23', '.1.3.6.1.2.1.4.32.1.5.16.1.10.86.60.0.27'])
    ('23', AugmentedIPv4Interface('10.86.60.1/27'))
    """
    match entry:
        # this checks the input against our expectation regarding types and structure
        case (str() as oid_end, list() as _dec_ip_address, str() as if_index, str() as _ip_prefix):
            dec_ip_address = list(map(int, _dec_ip_address))
            ip_prefix = _ip_prefix.split(".")[-1]
        case _:
            return None

    try:
        # "<ADR_TYPE>.<ADR_LENGTH>.<ADDRESS*>"
        adr_type, oid_adr_length, *oid_adr = list(map(int, oid_end.split(".")))
    except ValueError:
        # in case we can't parse the OID using the above pattern we assume this is not for us
        return None

    if (prefix := ("64" if oid_end.startswith("4.20.254.128.") else ip_prefix)) == "0":
        return None

    adr_length, raw_address = (
        (len(dec_ip_address), dec_ip_address) if dec_ip_address else (oid_adr_length, oid_adr)
    )

    if not (address_str := address_str_from(adr_type, adr_length, raw_address)):
        return None

    interface_ip = AugmentedIPInterface.from_ip_address(f"{address_str}/{prefix}")

    if interface_ip.ip.compressed == interface_ip.network.broadcast_address.compressed:
        return None  # drop broadcast IPs

    if interface_ip.ip.is_loopback:
        return None  # drop localhost

    if interface_ip.ip.exploded == "0.0.0.0":
        return None  # drop this host address

    return if_index, interface_ip


def ip_info_20_from(
    entry: Sequence[str | Sequence[int]],
) -> None | tuple[str, AugmentedIPv4Interface | AugmentedIPv6Interface]:
    """
    >>> ip_info_20_from(('12.12.12.1', '23', '3'))
    ('23', AugmentedIPv4Interface('12.12.12.1/3'))
    """
    match entry:
        # this checks the input against our expectation regarding types and structure
        case (str() as _raw_address, str() as if_index, str() as _raw_netmask):
            if not (_raw_address and if_index and _raw_netmask):
                return None
            if _raw_address == "0.0.0.0":  # storage-isilon-onefs
                return None
            interface_ip = AugmentedIPInterface.from_ip_address(f"{_raw_address}/{_raw_netmask}")
        case _:
            return None

    if interface_ip.ip.is_loopback:
        return None  # drop localhost

    if interface_ip.ip.exploded == "0.0.0.0":
        return None  # drop this host address

    return if_index, interface_ip


def parse_ip_addresses(string_table: Sequence[StringByteTable]) -> Section:
    ip_info_20, ip_info_34, if_info = string_table

    interface_by_index = {str(if_index): str(if_name) for if_index, if_name in if_info}

    result: dict[str, IPNetworkAdapter] = {}

    for if_index, interface_ip in (
        entry
        for entries in (
            map(ip_info_34_from, ip_info_34),
            map(ip_info_20_from, ip_info_20),
        )
        for entry in entries
        if entry
    ):
        name = interface_by_index.get(if_index, if_index)
        adapter = result.setdefault(name, IPNetworkAdapter(name=name, inet4=[], inet6=[]))
        if interface_ip.version == 4:
            adapter.inet4.append(interface_ip)
        elif interface_ip.version == 6:
            adapter.inet6.append(interface_ip)

    return list(result.values())


def host_labels_if_snmp(section: Section) -> HostLabelGenerator:
    """
    Host label function
    Labels:
        cmk/l3v4_topology:
            "singlehomed" is set for all devices with one IPv4 address
            "multihomed" is set for all devices with more than one IPv4 address.
        cmk/l3v6_topology:
            "singlehomed" is set for all devices with one IPv6 address
            "multihomed" is set for all devices with more than one IPv6 address.

        Link-local ("FE80::/64), unspecified ("::") and local-host ("127.0.0.0/8", "::1") IPs don't count.
    """
    yield from host_labels_if(section)


snmp_section_ip_address = SNMPSection(
    name="ip_addresses",
    parse_function=parse_ip_addresses,
    host_label_function=host_labels_if_snmp,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.4.20.1",  #  IP-MIB::ipAddrEntry
            oids=[
                "1",  #                     ipAdEntAddr
                "2",  #                     ipAdEntIfIndex
                "3",  #                     ipAdEntNetMask
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.4.34.1",  #  IP-MIB::ipAddrEntry
            oids=[
                OIDEnd(),  #                type.length.ip-address
                OIDBytes("2"),  #           ipAddressAddr
                "3",  #                     ipAddressIfIndex
                "5",  #                     ipAddressPrefix
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.31.1.1.1",
            oids=[
                OIDEnd(),  #                ifIndex
                "1",  #                     ifName
            ],
        ),
    ],
    detect=exists(".1.3.6.1.2.1.4.20.1.1.*"),
)


def inventorize_ip_addresses_snmp(section: Section) -> InventoryResult:
    yield from inventorize_ip_addresses(section)


inventory_plugin_ip_address = InventoryPlugin(
    name="ip_addresses",
    inventory_function=inventorize_ip_addresses_snmp,
)
