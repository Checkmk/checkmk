#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Iterable

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
    AugmentedIPv4Interface,
    AugmentedIPv6Interface,
    IPNetworkAdapter,
)
from cmk.plugins.lib.inventory_interfaces import inventorize_ip_addresses

Section = Iterable[IPNetworkAdapter]


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
    yield from host_labels_if(section)


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
    ...     ['Parameters', 'fe80::89d8:dead:beef:4223%23 RouterAdvertisement Random,10.11.12.14 WellKnown Link'],
    ...     ['AdapterType', 'T2'],
    ...     ['MACAddress', 'BE:EF'],
    ...     ['Name', 'Name2'],
    ...     ['Speed', '200'],
    ...     ['Address', '169.178.23.42 fe80::c118:dead:beef:2342'],
    ...     ['Subnet', '255.255.0.0 64'],
    ... ]): print(parsed_adapter)
    IPNetworkAdapter(name='Name1', type='T1', state_infos=None, link_ether='', macaddress='DE:AD', gateway='10.11.12.1', speed=100, inet4=[AugmentedIPv4Interface('10.11.12.13/24'), AugmentedIPv4Interface('10.11.12.14/24')], inet6=[AugmentedIPv6Interface('fe80::89d8:dead:beef:4223/64', is_temporary=True)])
    IPNetworkAdapter(name='Name2', type='T2', state_infos=None, link_ether='', macaddress='BE:EF', gateway='', speed=200, inet4=[AugmentedIPv4Interface('169.178.23.42/16')], inet6=[AugmentedIPv6Interface('fe80::c118:dead:beef:2342/64', is_temporary=False)])
    """

    def group_adapters(split_lines: StringTable) -> Iterable[dict]:
        first_varname = None
        result: dict = {"addrv4": [], "addrv6": [], "subnv4": [], "subnv6": [], "params": {}}

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
                result = {"addrv4": [], "addrv6": [], "subnv4": [], "subnv6": [], "params": {}}

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
            elif varname == "Parameters":
                result["params"] = {
                    key.split("%")[0].strip(): value.split()
                    for entry in value.lower().split(",")
                    for key, value in (entry.strip().split(maxsplit=1),)
                }
        if result.get("Name"):
            yield result

    return [
        IPNetworkAdapter(
            type=adapter.get("AdapterType", ""),
            macaddress=adapter.get("MACAddress", ""),
            name=adapter["Name"],
            speed=int(adapter["Speed"]) if "Speed" in adapter else 0,
            gateway=adapter.get("DefaultGateway", ""),
            inet4=[
                AugmentedIPv4Interface(f"{address}/{subnet}")
                for address, subnet in zip(adapter["addrv4"], adapter["subnv4"])
            ],
            inet6=[
                AugmentedIPv6Interface(f"{address}/{subnet}", is_temporary=is_temporary)
                for address, subnet in zip(adapter["addrv6"], adapter["subnv6"])
                for is_temporary in ("random" in (adapter["params"].get(address) or []),)
            ],
        )
        for adapter in group_adapters(string_table)
    ]


agent_section_win_networkadapter = AgentSection(
    name="win_networkadapter",
    parse_function=parse_win_networkadapter,
    host_label_function=host_label_win_ip_address,
)


def inventorize_win_networkadapter(section: Section) -> InventoryResult:
    for adapter in sorted(section, key=lambda a: a.name):
        yield TableRow(
            path=["hardware", "nwadapter"],
            key_columns={
                "name": adapter.name,
            },
            inventory_columns={
                "type": adapter.type,
                "macaddress": adapter.macaddress,
                "speed": adapter.speed,
                "gateway": adapter.gateway,
            },
            status_columns={},
        )


inventory_plugin_win_networkadapter = InventoryPlugin(
    name="win_networkadapter",
    inventory_function=inventorize_win_networkadapter,
)


def inventorize_ip_addresses_windows(section: Section) -> InventoryResult:
    yield from inventorize_ip_addresses(section)


inventory_plugin_win_ip_address = InventoryPlugin(
    name="win_ip_address",
    sections=["win_networkadapter"],
    inventory_function=inventorize_ip_addresses_windows,
)
