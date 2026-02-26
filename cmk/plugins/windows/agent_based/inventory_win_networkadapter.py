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

from collections.abc import Iterable, Mapping, Sequence
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
    HostLabelGenerator,
    InventoryPlugin,
    InventoryResult,
    StringTable,
    TableRow,
)
from cmk.plugins.lib.host_labels_interfaces import host_labels_if
from cmk.plugins.lib.interfaces import (
    IPNetworkAdapter,
)
from cmk.plugins.lib.inventory_interfaces import inventorize_ip_addresses

Section = Iterable[Mapping[str, str]]


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
    yield from host_labels_if(
        IPNetworkAdapter(
            name=adapter.name,
            inet4=[ip_if for ip_if in interfaces if isinstance(ip_if, IPv4Interface)],
            inet6=[ip_if for ip_if in interfaces if isinstance(ip_if, IPv6Interface)],
        )
        for adapter in map(Adapter.model_validate, section)
        if (interfaces := adapter.interface_ips())
    )


def parse_win_networkadapter(string_table: StringTable) -> Section:
    """
    >>> for parsed_adapter in parse_win_networkadapter([
    ...     ['AdapterType', 'T1'],
    ...     ['MACAddress', 'DE:AD'],
    ...     ['Name', 'Name1'],
    ...     ['Speed', '100'],
    ...     ['Address', '10.11.12.13 10.11.12.14 fe80::89d8:dead:beef:4223'],
    ...     ['Subnet', '255.255.255.0 255.255.255.0 64'],
    ...     ['DefaultGateway', '10.11.12.1'],
    ...     ['AdapterType', 'T2'],
    ...     ['MACAddress', 'BE:EF'],
    ...     ['Name', 'Name2'],
    ...     ['Speed', '200'],
    ...     ['Address', '169.178.23.42 fe80::c118:dead:beef:2342'],
    ...     ['Subnet', '255.255.0.0 64'],
    ... ]): print(parsed_adapter)
    {'name': 'Name1', 'type': 'T1', 'macaddress': 'DE:AD', 'speed': 100, 'gateway': '10.11.12.1', 'ipv4_address': '10.11.12.13, 10.11.12.14', 'ipv6_address': 'fe80::89d8:dead:beef:4223', 'ipv4_subnet': '255.255.255.0, 255.255.255.0', 'ipv6_subnet': '64'}
    {'name': 'Name2', 'type': 'T2', 'macaddress': 'BE:EF', 'speed': 200, 'ipv4_address': '169.178.23.42', 'ipv6_address': 'fe80::c118:dead:beef:2342', 'ipv4_subnet': '255.255.0.0', 'ipv6_subnet': '64'}
    """

    def group_adapters(split_lines: StringTable) -> Iterable[dict]:
        first_varname = None
        result: dict = {"addrv4": [], "addrv6": [], "subnv4": [], "subnv6": []}

        for varname, value in (
            (element[0].strip(), value)
            for element in split_lines
            if len(element) >= 2
            # glue `value` together again (has been split by `sep(58)`)
            if (value := ":".join(element[1:]).strip())
        ):
            # Check whether we have a new instance
            # if we meet varname again, then we assume that this
            # is new instance
            if first_varname and varname == first_varname:
                yield result
                result = {"addrv4": [], "addrv6": [], "subnv4": [], "subnv6": []}

            if not first_varname:
                first_varname = varname

            if varname in ("Name", "AdapterType", "MACAddress", "Speed", "DefaultGateway"):
                result[varname] = value
            elif varname == "Address":
                for address in value.split(" "):
                    result.setdefault("addrv6" if ":" in address else "addrv4", []).append(address)
            elif varname == "Subnet":
                for address in value.split(" "):
                    result.setdefault("subnv4" if "." in address else "subnv6", []).append(address)
        if result.get("Name"):
            yield result

    for adapter in group_adapters(string_table):
        result = {
            "name": adapter["Name"],
            "type": adapter["AdapterType"],
        }
        if "MACAddress" in adapter:
            result["macaddress"] = adapter["MACAddress"]
        if "Speed" in adapter:
            result["speed"] = int(adapter["Speed"])
        if "DefaultGateway" in adapter:
            result["gateway"] = adapter["DefaultGateway"]
        if "addrv4" in adapter:
            result["ipv4_address"] = ", ".join(adapter["addrv4"])
        if "addrv6" in adapter:
            result["ipv6_address"] = ", ".join(adapter["addrv6"])
        if "subnv4" in adapter:
            result["ipv4_subnet"] = ", ".join(adapter["subnv4"])
        if "subnv6" in adapter:
            result["ipv6_subnet"] = ", ".join(adapter["subnv6"])

        yield result


agent_section_win_networkadapter = AgentSection(
    name="win_networkadapter",
    parse_function=parse_win_networkadapter,
    # refactor-me: should use cmk.plugins.network.agent_based.ip_addresses.host_label_ip_addresses
    #              but that has to be refactored first to use Adapter
    host_label_function=host_label_win_ip_address,
)


def inventory_win_networkadapter(section: Section) -> InventoryResult:
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


def inventory_win_ip_address(section: Section) -> InventoryResult:
    """
    >>> list(inventory_win_ip_address([{
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
    yield from inventorize_ip_addresses(
        IPNetworkAdapter(
            name=adapter.name,
            inet4=[ip_if for ip_if in interfaces if isinstance(ip_if, IPv4Interface)],
            inet6=[ip_if for ip_if in interfaces if isinstance(ip_if, IPv6Interface)],
        )
        for adapter in map(Adapter.model_validate, section)
        if (interfaces := adapter.interface_ips())
    )


inventory_plugin_win_networkadapter = InventoryPlugin(
    name="win_networkadapter",
    inventory_function=inventory_win_networkadapter,
)

inventory_plugin_win_ip_address = InventoryPlugin(
    name="win_ip_address",
    sections=["win_networkadapter"],
    inventory_function=inventory_win_ip_address,
)
