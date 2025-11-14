#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2024-09-30
# File  : inv_win_ip_address.py

# based on inventory_win_networkadapter.py

# 2024-11-29: added host label section
# 2024-12-02: changed host label to nvdct/l3v4_host:yes and nvdct/l3v4_routing:yes
# 2024-12-03: fixed crash in host label function on missing ipv4_address
#             added support for IPv6 addresses
#             added support for multiple IPs per interface
# 2024-12-05  changed to use ip_interface
# 2024-12-06: changed host label to nvdct/l3v4_topology:host and nvdct/l3v4_topology:router
# 2024-12-09: rewritten for CMK checkAPI 2.0
# 2024-12-10: added host label nvdct/l3v6_topology:host and nvdct/l3v6_topology:router
# 2014-12-12: fix crash in host label function if interface has no ip-address
# 2025-01-21: added drop broadcast IPs
# 2025-01-24: fixed crash on bad prefix-length (to long for the ip version i.e. 33 for ipv4)
# 2025-03-23: changed to work with CMK 2.4.0x

from collections.abc import Mapping, Sequence
from ipaddress import AddressValueError, IPv4Interface, IPv6Interface, NetmaskValueError, ip_interface
from pydantic import BaseModel, computed_field
from pydantic.functional_validators import AfterValidator
from typing_extensions import Annotated

from cmk.agent_based.v2 import (
    AgentSection,
    HostLabel,
    HostLabelGenerator,
    InventoryPlugin,
    InventoryResult,
    TableRow,
)
from cmk.plugins.collection.agent_based.inventory_win_networkadapter import parse_win_networkadapter

Section = Sequence[Mapping]

__section = [
    {
        'type': ' Ethernet 802.3',
        'macaddress': ' 3C:7C:3F:49:7C:22',
        'name': ' ASUS USB-AC68 USB Wireless adapter',
        'speed': 1300000000,
        'ipv4_address': ', 192.168.10.11',
        'ipv6_subnet': '',
        'ipv4_subnet': '255.255.255.0'
    },
    {
        'type': ' Ethernet 802.3',
        'name': ' VMware Virtual Ethernet Adapter for VMnet1',
        'macaddress': ' 00:50:56:C0:00:01',
        'speed': 100000000,
        'ipv4_address': ', 169.254.0.1, 192.168.1.100',
        'ipv4_subnet': '255.255.0.0, 255.255.255.0',
        'ipv6_address': 'fe80::5669:a1eb:3add:e9b2, 2c::1',
        'ipv6_subnet': ', 64, 127',
    },
    {
        'type': ' Ethernet 802.3',
        'macaddress': ' 00:1A:7D:DA:71:06',
        'name': ' Bluetooth Device (Personal Area Network)'
    },
    {
        'type': ' Ethernet 802.3',
        'macaddress': ' 3E:7C:3F:49:7C:22',
        'name': ' Microsoft Wi-Fi Direct Virtual Adapter',
        'speed': 9223372036854775807
    },
    {
        'type': ' Ethernet 802.3',
        'macaddress': ' 3C:7C:3F:49:7C:22',
        'name': ' Microsoft Wi-Fi Direct Virtual Adapter #2',
        'speed': 9223372036854775807
    }
]


def clean_str(v: str) -> str:
    v = v.strip().strip(',').strip()
    return v


CleanStr = Annotated[str, AfterValidator(clean_str)]

def is_broadcast(interface_ip: ip_interface) -> bool:
    if interface_ip.version == 4 and interface_ip.network.prefixlen != 32:
        if interface_ip.ip.compressed == interface_ip.network.broadcast_address.compressed:
            return True
    elif interface_ip.version == 6 and interface_ip.network.prefixlen != 128:
        if interface_ip.ip.compressed == interface_ip.network.broadcast_address.compressed:
            return True

    return False


class Adapter(BaseModel):
    name: CleanStr
    ipv4_address: CleanStr | None = None
    ipv4_subnet: CleanStr | None = None
    ipv6_address: CleanStr | None = None
    ipv6_subnet: CleanStr | None = None

    @staticmethod
    def add_ip_data(ip_addresses: str, ip_subnets: str):
        raw_address = ip_addresses.split(', ')
        raw_networks = ip_subnets.split(', ')
        _ip_data = []

        for i in range(0, len(raw_address)):
            try:
                interface_ip = ip_interface(f'{raw_address[i]}/{raw_networks[i]}')
            except (AddressValueError, NetmaskValueError, ValueError):
                continue

            if is_broadcast(interface_ip):
                continue  # drop broadcast IPs

            _ip_data.append(interface_ip)

        return _ip_data

    @computed_field
    @property
    def interface_ips(self) -> Sequence[ip_interface]:
        _ip_data = []
        if self.ipv4_address and self.ipv4_subnet:
            _ip_data += self.add_ip_data(self.ipv4_address, self.ipv4_subnet)

        if self.ipv6_address and self.ipv6_subnet:
            _ip_data += self.add_ip_data(self.ipv6_address, self.ipv6_subnet)

        return _ip_data


__adapter = Adapter(
    name='VMware Virtual Ethernet Adapter for VMnet1',
    ipv4_address='169.254.0.1, 192.168.1.100',
    ipv4_subnet='255.255.0.0, 255.255.255.0',
    ipv6_address='fe80::5669:a1eb:3add:e9b2, 2c::1',
    ipv6_subnet='64, 127',
    ip_data=[
        IPv4Interface('169.254.0.1/16'),
        IPv4Interface('192.168.1.100/24'),
        IPv6Interface('fe80::5669:a1eb:3add:e9b2/64'),
        IPv6Interface('2c::1/127')
    ]
)


def host_label_win_ip_address(section: Section) -> HostLabelGenerator:
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
    for raw_adapter in section:
        adapter = Adapter.model_validate(raw_adapter)
        for interface_ip in adapter.interface_ips:
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


agent_section_inv_win_ip_address = AgentSection(
    name="win_networkadapter",
    parse_function=parse_win_networkadapter,
    host_label_function=host_label_win_ip_address
)


def inventory_win_ip_address(section: Section) -> InventoryResult:
    address_type = {
        4: 'ipv4',
        6: 'ipv6',
    }
    for raw_adapter in section:
        adapter = Adapter.model_validate(raw_adapter)

        if adapter.name and adapter.interface_ips:
            for interface_ip in adapter.interface_ips:
                yield TableRow(
                    path=['networking', 'addresses'],
                    key_columns={
                        'address': str(interface_ip.ip.compressed),
                        'device': adapter.name,
                    },
                    inventory_columns={
                        'broadcast': str(interface_ip.network.broadcast_address),
                        'cidr': interface_ip.network.prefixlen,
                        'netmask': str(interface_ip.network.netmask),
                        'network': str(interface_ip.network.network_address),
                        'type': address_type.get(interface_ip.version).lower(),
                    },
                    status_columns={},
                )


inventory_plugin_inv_win_ip_address = InventoryPlugin(
    name='win_ip_address',
    sections=['win_networkadapter'],
    inventory_function=inventory_win_ip_address,
)
