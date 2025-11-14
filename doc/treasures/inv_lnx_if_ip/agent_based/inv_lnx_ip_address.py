# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2024-07-12
# File  : plugins/agent_based/inv_lnx_ip_address.py

# based on ~/lib/check_mk/base/plugins/agent_based/lnx_if.py

# 2024-12-02: incompatible changed host label to nvdct/l3v4_host:yes and nvdct/l3v4_routing:yes
# 2024-12-05  changed to use ip_interface
# 2024-12-06: incompatible: changed hostlabel to nvdct/l3v4_topology:host and nvdct/l3v4_topology:router
# 2024-12-09: rewritten for CMK checkAPI 2.0
# 2024-12-10: added host label nvdct/l3v6_topology:host and nvdct/l3v6_topology:router
# 2025-01-21: added drop broadcast IPs
# 2025-01-24: fixed crash on bad prefix-length (to long for the ip version i.e. 33 for ipv4)
# 2025-03-23: changed to work with CMK 2.4.0x


from collections.abc import MutableMapping, MutableSequence, Sequence
from dataclasses import dataclass, field
from ipaddress import AddressValueError, NetmaskValueError, ip_interface

from cmk.agent_based.v2 import (
    AgentSection,
    HostLabel,
    HostLabelGenerator,
    InventoryPlugin,
    InventoryResult,
    TableRow,
)

## from cmk.base.plugins.agent_based.lnx_if import parse_lnx_if
from cmk.plugins.collection.agent_based.lnx_if import parse_lnx_if


@dataclass
class IPLinkInterface:
    state_infos: Sequence[str] | None = None
    link_ether: str = ""
    inet: MutableSequence[str] = field(default_factory=list)
    inet6: MutableSequence[str] = field(default_factory=list)


SectionInventory = MutableMapping[str, IPLinkInterface]

__section_inventory = {
    'lo': IPLinkInterface(
        state_infos=['LOOPBACK', 'UP', 'LOWER_UP'],
        link_ether='',
        inet=['127.0.0.1/8'],
        inet6=['::1/128']
    ),
    'ens32': IPLinkInterface(
        state_infos=['BROADCAST', 'MULTICAST', 'UP', 'LOWER_UP'],
        link_ether='\x00\x0c)\x82ýr',
        inet=['192.168.10.144/24'],
        inet6=['fe80::20c:29ff:fe82:fd72/64']
    )
}


def host_label_lnx_ip_address(section: SectionInventory) -> HostLabelGenerator:
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
    _interfaces_with_counters, ip_stats = section
    for if_name, interface in ip_stats.items():
        for raw_interface_ips, _ in [
            (interface.inet, "ipv4"),
            (interface.inet6, "ipv6"),
        ]:
            for raw_interface_ip in raw_interface_ips:
                try:
                    interface_ip = ip_interface(raw_interface_ip)
                except (AddressValueError, NetmaskValueError,ValueError):
                    continue
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



## agent_section_lnx_if = AgentSection(
##     name="lnx_if",
##     parse_function=parse_lnx_if,
##     supersedes=["if", "if64"],
## )

## agent_section_inv_lnx_ip_address = AgentSection(
agent_section_lnx_if = AgentSection(
    name="lnx_if",
    parse_function=parse_lnx_if,
    supersedes=["if", "if64"],
    host_label_function=host_label_lnx_ip_address
)


def inventory_lnx_if_ip(section: SectionInventory) -> InventoryResult:
    address_type = {
        4: 'ipv4',
        6: 'ipv6',
    }
    _interfaces_with_counters, ip_stats = section
    for if_name, interface in ip_stats.items():
        raw_interface_ips = interface.inet + interface.inet6
        for raw_interface_ip in raw_interface_ips:
            try:
                interface_ip = ip_interface(raw_interface_ip)
            except (AddressValueError, NetmaskValueError):
                continue

            if interface_ip.ip.compressed == interface_ip.network.broadcast_address.compressed:
                continue  # drop broadcast IPs

            yield TableRow(
                path=["networking", "addresses"],
                key_columns={
                    "address": str(interface_ip.ip.compressed),
                    "device": if_name,
                },
                inventory_columns={
                    "broadcast": str(interface_ip.network.broadcast_address),
                    "cidr": interface_ip.network.prefixlen,
                    "netmask": str(interface_ip.network.netmask),
                    "network": str(interface_ip.network.network_address),
                    "type": address_type.get(interface_ip.version).lower(),
                },
            )


inventory_plugin_inv_lnx_ip_address = InventoryPlugin(
    name="inv_lnx_if_ip",
    sections=["lnx_if"],
    inventory_function=inventory_lnx_if_ip,
)
