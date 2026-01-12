#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

# Example output:
# <<<win_networkadapter:sep(58)>>>
# AdapterType: Ethernet 802.3
# DeviceID: 7
# MACAddress: 08:00:27:9C:F8:39
# Name: Intel(R) PRO/1000 MT-Desktopadapter
# NetworkAddresses:
# ServiceName: E1G60
# Speed: 1000000000
# Address: 192.168.178.26
# Subnet: 255.255.255.0
# DefaultGateway: 192.168.178.1

from collections.abc import Mapping, Sequence
from contextlib import suppress
from ipaddress import (
    AddressValueError,
    ip_interface,
    IPv4Interface,
    IPv6Interface,
    NetmaskValueError,
)

from pydantic import BaseModel, field_validator

from cmk.agent_based.v2 import (
    AgentSection,
    HostLabel,
    HostLabelGenerator,
    InventoryPlugin,
    InventoryResult,
    StringTable,
    TableRow,
)

Section = Sequence[Mapping[str, str]]


class Adapter(BaseModel):
    # Original author: thl-cmk[at]outlook[dot]com
    #
    # refactor-me: this model should be moved to cmk.plugins.lib and used for other plugins, too,
    #              e.g. lnx_if and ip_addresses
    name: str
    ipv4_address: str | None = None
    ipv4_subnet: str | None = None
    ipv6_address: str | None = None
    ipv6_subnet: str | None = None

    @staticmethod
    def is_broadcast(interface: IPv4Interface | IPv6Interface) -> bool:
        """
        >>> Adapter.is_broadcast(IPv4Interface("1.2.3.4/24"))
        False
        """
        return (
            (interface.version == 4 and interface.network.prefixlen != 32)
            or (interface.version == 6 and interface.network.prefixlen != 128)
        ) and (interface.ip.compressed == interface.network.broadcast_address.compressed)

    def interface_ips(self) -> Sequence[IPv4Interface | IPv6Interface]:
        def interface_from(address: str, subnet: str) -> None | IPv4Interface | IPv6Interface:
            """Returns an interface instance from valid non-broadcast input"""
            with suppress(AddressValueError, NetmaskValueError, ValueError):
                # drop broadcast IPs
                if not Adapter.is_broadcast(ip_if := ip_interface(f"{address}/{subnet}")):
                    return ip_if
            return None

        return [
            interface
            for addresses, subnets in (
                (self.ipv4_address, self.ipv4_subnet),
                (self.ipv6_address, self.ipv6_subnet),
            )
            if addresses and subnets
            for raw_address, raw_subnet in zip(addresses.split(", "), subnets.split(", "))
            if (interface := interface_from(raw_address, raw_subnet))
        ]

    @field_validator("*", mode="after")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return value.strip().strip(",").strip()


def host_label_win_ip_address(section: Section) -> HostLabelGenerator:
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
    # Original author: thl-cmk[at]outlook[dot]com
    #
    # refactor-me: this should go to cmk.plugins.network.agent_based.ip_addresses.host_label_ip_addresses
    #              but callers first have to use Adapter
    valid_v4_ips = 0
    valid_v6_ips = 0
    for raw_adapter in section:
        adapter = Adapter.model_validate(raw_adapter)
        for interface_ip in adapter.interface_ips():
            if interface_ip.version == 4 and not interface_ip.is_loopback:
                valid_v4_ips += 1
                if valid_v4_ips == 1:
                    yield HostLabel(name="cmk/l3v4_topology", value="singlehomed")
                if valid_v4_ips == 2:
                    yield HostLabel(name="cmk/l3v4_topology", value="multihomed")

            elif (
                interface_ip.version == 6
                and not interface_ip.is_loopback
                and not interface_ip.is_link_local
                and not interface_ip.is_unspecified
            ):
                valid_v6_ips += 1
                if valid_v6_ips == 1:
                    yield HostLabel(name="cmk/l3v6_topology", value="singlehomed")
                if valid_v6_ips == 2:
                    yield HostLabel(name="cmk/l3v6_topology", value="multihomed")


def parse_win_networkadapter(
    string_table: StringTable,
) -> Section:
    adapters: list[Mapping] = []
    first_varname = None
    array: dict = {}
    addrtypes: dict = {}

    for line in string_table:
        # return 'lost' double-colons back
        if len(line) < 2:
            continue

        stripped_line = [w.strip() for w in line]
        varname = stripped_line[0]
        value = ":".join(line[1:])

        # empty? skip!
        if not value:
            continue

        # Check whether we have a new instance
        # if we meet varname again, then we assume that this
        # is new instance
        if first_varname and varname == first_varname:
            adapters.append(array)
            array = {}
            addrtypes = {}

        if not first_varname:
            first_varname = varname

        if varname == "Name":
            array["name"] = value
        elif varname == "AdapterType":
            array["type"] = value
        elif varname == "MACAddress":
            array["macaddress"] = value
        elif varname == "Speed":
            array["speed"] = int(value)
        elif varname == "Address":
            for address in value.split(" "):
                addrtype = "ipv6" if ":" in address else "ipv4"
                addrtypes.setdefault(addrtype + "_address", []).append(address)
        elif varname == "Subnet":
            for address in value.split(" "):
                addrtype = "ipv4" if "." in address else "ipv6"
                addrtypes.setdefault(addrtype + "_subnet", []).append(address)
        elif varname == "DefaultGateway":
            array["gateway"] = value

        # address string array in comma-separated string packing: ['a1','a2',...] -> 'a1,a2...'
        for addrtype in addrtypes:
            array[addrtype] = ", ".join(addrtypes[addrtype])

    # Append last array
    if array:
        adapters.append(array)
    return adapters


agent_section_win_networkadapter = AgentSection(
    name="win_networkadapter",
    parse_function=parse_win_networkadapter,
    # refactor-me: should use cmk.plugins.network.agent_based.ip_addresses.host_label_ip_addresses
    #              but that has to be refactored first to use Adapter
    host_label_function=host_label_win_ip_address,
)


def inventorize_win_networkadapter(section: Section) -> InventoryResult:
    for adapter in sorted(section, key=lambda a: a.get("name", "")):
        if "name" in adapter:
            yield TableRow(
                path=["hardware", "nwadapter"],
                key_columns={
                    "name": adapter["name"],
                },
                inventory_columns={
                    "type": adapter.get("type"),
                    "macaddress": adapter.get("macaddress"),
                    "speed": adapter.get("speed"),
                    "gateway": adapter.get("gateway"),
                    "ipv4_address": adapter.get("ipv4_address"),
                    "ipv6_address": adapter.get("ipv6address"),
                    "ipv4_subnet": adapter.get("ipv4_subnet"),
                    "ipv6_subnet": adapter.get("ipv6subnet"),
                },
                status_columns={},
            )


def inventorize_win_ip_address(section: Section) -> InventoryResult:
    """
    >>> list(inventorize_win_ip_address([{
    ...    "type": "ETH 802.3",
    ...    "macaddress": " 3C:7C:3F:49:7C:22",
    ...    "name": "Adaptor",
    ...    "speed": 23,
    ...    "ipv4_address": ", 1.2.3.4",
    ...    "ipv6_subnet": "",
    ...    "ipv4_subnet": "255.255.255.0",
    ... }]))
    [TableRow(path=['networking', 'addresses'], key_columns={'address': '1.2.3.4', 'device': 'Adaptor'}, inventory_columns={'type': 'ipv4', 'network': '1.2.3.0', 'netmask': '255.255.255.0', 'prefixlength': 24, 'broadcast': '1.2.3.255'}, status_columns={})]
    """
    # Original author: thl-cmk[at]outlook[dot]com
    #
    # refactor-me: this should go to cmk.plugins.network.agent_based.ip_addresses.host_label_ip_addresses
    #              but callers first have to use Adapter
    address_type = {
        4: "ipv4",
        6: "ipv6",
    }

    yield from (
        TableRow(
            path=["networking", "addresses"],
            key_columns={
                "address": str(interface.ip.compressed),
                "device": adapter.name,
            },
            inventory_columns={
                "type": address_type.get(interface.version, "").lower(),
                "network": str(interface.network.network_address),
                "netmask": str(interface.network.netmask),
                "prefixlength": interface.network.prefixlen,
                "broadcast": str(interface.network.broadcast_address),
            },
            status_columns={},
        )
        for adapter in map(Adapter.model_validate, section)
        if adapter.name
        for interface in adapter.interface_ips()
    )


inventory_plugin_win_networkadapter = InventoryPlugin(
    name="win_networkadapter",
    inventory_function=inventorize_win_networkadapter,
)

inventory_plugin_win_ip_address = InventoryPlugin(
    name="win_ip_address",
    sections=["win_networkadapter"],
    inventory_function=inventorize_win_ip_address,
)
