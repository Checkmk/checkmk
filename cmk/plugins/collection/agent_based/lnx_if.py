#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, MutableMapping, MutableSequence, Sequence
from dataclasses import dataclass, field, replace
from typing import Any, Literal

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    InventoryPlugin,
    InventoryResult,
    RuleSetType,
    StringTable,
    TableRow,
)
from cmk.plugins.lib import bonding, interfaces
from cmk.plugins.lib.interfaces import InterfaceWithCounters
from cmk.plugins.lib.inventory_interfaces import Interface as InterfaceInv
from cmk.plugins.lib.inventory_interfaces import inventorize_interfaces

# Example output from agent:

# <<<lnx_if>>>
# [start_iplink]
# 1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN mode DEFAULT group default
#     link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
#     inet 127.0.0.1/8 scope host lo
#       valid_lft forever preferred_lft forever
#     inet6 ::1/128 scope host
#       valid_lft forever preferred_lft forever
# 2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP mode DEFAULT group default qlen 1000
#     link/ether 00:27:13:b4:a9:ec brd ff:ff:ff:ff:ff:ff
#     inet 127.0.0.1/8 scope host lo
#       valid_lft forever preferred_lft forever
#     inet6 ::1/128 scope host
#       valid_lft forever preferred_lft forever
# 3: eth1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP mode DORMANT group default qlen 1000
#     link/ether 00:21:6a:10:8e:b8 brd ff:ff:ff:ff:ff:ff
#     inet 127.0.0.1/8 scope host lo
#       valid_lft forever preferred_lft forever
#     inet6 ::1/128 scope host
#       valid_lft forever preferred_lft forever
# [end_iplink]
# <<<lnx_if:sep(58)>>>
#    lo:   4520   54  0  0  0  0  0  0    4520  54    0   0   0   0   0   0
#  eth0:      0    0  0  0  0  0  0  0    1710   5    0   0   0   0   0   0
#  eth1:  78505  555  0  0  0  0  0  0  132569  523   0   0   0   0   0    0
# [lo]
#         Link detected: yes
# [eth0]
#         Speed: 65535Mb/s
#         Duplex: Unknown! (255)
#         Auto-negotiation: on
#         Link detected: no
#         Address: de:ad:be:af:00:01
# [eth1]
#         Speed: 1000Mb/s
#         Duplex: Full
#         Auto-negotiation: on
#         Link detected: yes


@dataclass
class EthtoolInterface:
    ethtool_index: str | None = None
    counters: Sequence[int] = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    address: str = ""
    speed: int = 0
    link_detected: str | None = None


@dataclass
class IPLinkInterface:
    state_infos: Sequence[str] | None = None
    link_ether: str = ""
    inet: MutableSequence[str] = field(default_factory=list)
    inet6: MutableSequence[str] = field(default_factory=list)


EthtoolSection = Mapping[str, EthtoolInterface]
SectionInventory = MutableMapping[str, IPLinkInterface]
Section = tuple[Sequence[InterfaceWithCounters], SectionInventory]


def _parse_lnx_if_ipaddress(lines: Iterable[Sequence[str]]) -> SectionInventory:
    ip_stats: SectionInventory = {}
    iface = None
    for line in lines:
        if line == ["[end_iplink]"]:
            break

        if line[0].endswith(":") and line[1].endswith(":"):
            # Some (docker) interfaces have suffix "@..." but ethtool does not show this suffix.
            # 1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default ...
            # 5: veth6a06585@if4: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue ...
            iface = ip_stats.setdefault(
                line[1][:-1].split("@")[0], IPLinkInterface(state_infos=line[2][1:-1].split(","))
            )
            # The interface flags are summarized in the angle brackets.
            continue

        if not iface:
            continue

        if len(line) > 1 and line[0] == "link/ether":
            # link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
            # link/none
            iface.link_ether = _get_physical_address(line[1])

        if "temporary" in line and "dynamic" in line:
            continue
        if line[0] == "inet":
            # inet 127.0.0.1/8 scope host lo
            iface.inet.append(line[1])
        elif line[0] == "inet6":
            # inet6 ::1/128 scope host
            iface.inet6.append(line[1])
    return ip_stats


def _parse_lnx_if_sections(
    string_table: StringTable,
) -> tuple[SectionInventory, EthtoolSection]:
    ip_stats: dict[str, IPLinkInterface] = {}
    ethtool_stats: dict[str, EthtoolInterface] = {}
    iface = None
    lines = iter(string_table)
    ethtool_index = 0
    for line in lines:
        if line[0].startswith("[start_iplink]"):
            # Parse 'ip link/address' section (as fallback in case ethtool is missing)
            ip_stats.update(_parse_lnx_if_ipaddress(lines))

        elif len(line) == 2 and len(line[1].strip().split()) >= 16:
            # Parse '/proc/net/dev'
            # IFACE_NAME: VAL VAL VAL ...
            iface = ethtool_stats.setdefault(line[0], EthtoolInterface())
            iface.counters = list(map(int, line[1].strip().split()))
        elif line[0].startswith("[") and line[0].endswith("]"):
            # Parse 'ethtool' output
            # [IF_NAME]
            #       KEY: VAL
            #       KEY: VAL
            #       ...
            ethtool_index += 1
            iface = ethtool_stats.setdefault(line[0][1:-1], EthtoolInterface())
            iface.ethtool_index = str(ethtool_index)
        elif iface is not None:
            stripped_line0 = line[0].strip()
            if stripped_line0 == "Address":
                iface.address = _get_physical_address(":".join(line[1:]).strip())
            elif stripped_line0 == "Speed":
                iface.speed = _get_speed(line[1].strip())
            elif stripped_line0 == "Link detected":
                iface.link_detected = line[1].strip()
    return ip_stats, ethtool_stats


def _get_speed(speed_text: str) -> int:
    if speed_text == "65535Mb/s":  # unknown
        return 0
    if speed_text.endswith("Kb/s"):
        return int(float(speed_text[:-4])) * 1000
    if speed_text.endswith("Mb/s"):
        return int(float(speed_text[:-4])) * 1000_000
    if speed_text.endswith("Gb/s"):
        return int(float(speed_text[:-4])) * 1000_000_000
    return 0


def _get_oper_status(
    link_detected: str | None, state_infos: Sequence[str] | None, ifInOctets: int
) -> Literal["1", "2", "4"]:
    # Link state from ethtool. If ethtool has no information about
    # this NIC, we set the state to unknown.
    if link_detected == "yes":
        return "1"
    if link_detected == "no":
        return "2"

    # Assumption:
    # abc: <BROADCAST,MULTICAST,UP,LOWER_UP>    UP + LOWER_UP   => really UP
    # def: <NO-CARRIER,BROADCAST,MULTICAST,UP>  NO-CARRIER + UP => DOWN, but admin UP
    # ghi: <BROADCAST,MULTICAST>                unconfigured    => DOWN
    if state_infos is not None:
        if "UP" in state_infos and "LOWER_UP" in state_infos:
            return "1"
        return "2"

    # No information from ethtool. We consider interfaces up
    # if they have been used at least some time since the
    # system boot.
    if ifInOctets > 0:
        return "1"  # assume up
    return "4"  # unknown (NIC has never been used)


def _get_physical_address(address: str) -> str:
    if ":" in address:
        # We saw interface entries of tunnels for the address
        # is an integer, eg. '1910236'; especially on OpenBSD.
        return interfaces.mac_address_from_hexstring(address)
    return ""


def parse_lnx_if(string_table: StringTable) -> Section:
    ip_stats, ethtool_stats = _parse_lnx_if_sections(string_table)

    if_table = []
    for index, (nic, ethtool_interface) in enumerate(sorted(ethtool_stats.items())):
        ifInOctets = ethtool_interface.counters[0]
        iplink_interface = ip_stats.get(nic, IPLinkInterface())
        if_table.append(
            interfaces.InterfaceWithCounters(
                interfaces.Attributes(
                    index=ethtool_interface.ethtool_index or str(index + 1),
                    descr=nic,
                    type="24" if nic == "lo" else "6",  # Guess type from name of interface
                    speed=ethtool_interface.speed,
                    oper_status=_get_oper_status(
                        ethtool_interface.link_detected,
                        iplink_interface.state_infos,
                        ifInOctets,
                    ),
                    out_qlen=ethtool_interface.counters[12],
                    alias=nic,
                    phys_address=ethtool_interface.address or iplink_interface.link_ether,
                ),
                interfaces.Counters(
                    in_octets=ifInOctets,
                    in_ucast=ethtool_interface.counters[1] + ethtool_interface.counters[7],
                    in_mcast=ethtool_interface.counters[7],
                    in_bcast=0,
                    in_disc=ethtool_interface.counters[3],
                    in_err=ethtool_interface.counters[2],
                    out_octets=ethtool_interface.counters[8],
                    out_ucast=ethtool_interface.counters[9],
                    out_mcast=0,
                    out_bcast=0,
                    out_disc=ethtool_interface.counters[11],
                    out_err=ethtool_interface.counters[10],
                ),
            )
        )

    return if_table, ip_stats


agent_section_lnx_if = AgentSection(
    name="lnx_if",
    parse_function=parse_lnx_if,
    supersedes=["if", "if64"],
)


def discover_lnx_if(
    params: Sequence[Mapping[str, Any]],
    section_lnx_if: Section | None,
    section_bonding: bonding.Section | None,
) -> DiscoveryResult:
    if section_lnx_if is None:
        return
    # Always exclude dockers veth* interfaces on docker nodes
    if_table = [
        iface for iface in section_lnx_if[0] if not iface.attributes.descr.startswith("veth")
    ]
    yield from interfaces.discover_interfaces(
        params,
        if_table,
    )


def _fix_bonded_mac(
    interface: interfaces.InterfaceWithCounters,
    mac_map: Mapping[str, str],
) -> interfaces.InterfaceWithCounters:
    try:
        mac = mac_map.get(interface.attributes.alias) or mac_map[interface.attributes.descr]
    except KeyError:
        return interface
    return replace(
        interface,
        attributes=replace(
            interface.attributes,
            phys_address=interfaces.mac_address_from_hexstring(mac),
        ),
    )


def _get_fixed_bonded_if_table(
    section_lnx_if: Section,
    section_bonding: bonding.Section | None,
) -> interfaces.Section[interfaces.InterfaceWithCounters]:
    if not section_bonding:
        return section_lnx_if[0]
    mac_map = bonding.get_mac_map(section_bonding)
    return [_fix_bonded_mac(interface, mac_map) for interface in section_lnx_if[0]]


def check_lnx_if(
    item: str,
    params: Mapping[str, Any],
    section_lnx_if: Section | None,
    section_bonding: bonding.Section | None,
) -> CheckResult:
    if section_lnx_if is None:
        return

    yield from interfaces.check_multiple_interfaces(
        item,
        params,
        _get_fixed_bonded_if_table(section_lnx_if, section_bonding),
    )


def cluster_check_lnx_if(
    item: str,
    params: Mapping[str, Any],
    section_lnx_if: Mapping[str, Section | None],
    section_bonding: Mapping[str, bonding.Section | None],
) -> CheckResult:
    yield from interfaces.cluster_check(
        item,
        params,
        {
            node: _get_fixed_bonded_if_table(node_section, section_bonding.get(node))
            for node, node_section in section_lnx_if.items()
            if node_section is not None
        },
    )


check_plugin_lnx_if = CheckPlugin(
    name="lnx_if",
    sections=["lnx_if", "bonding"],
    service_name="Interface %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=discover_lnx_if,
    check_ruleset_name="interfaces",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=check_lnx_if,
    cluster_check_function=cluster_check_lnx_if,
)


def _make_inventory_interface(
    interface: interfaces.InterfaceWithCounters,
    mac_map: Mapping[str, str],
    bond_map: Mapping[str, str],
) -> InterfaceInv | None:
    # Always exclude dockers veth* interfaces on docker nodes.
    # Useless entries for "TenGigabitEthernet2/1/21--Uncontrolled".
    # Ignore useless half-empty tables (e.g. Viprinet-Router).
    if interface.attributes.descr.startswith("veth") or interface.attributes.type in ("231", "232"):
        return None

    mac = (
        mac_map.get(interface.attributes.descr)
        or mac_map.get(interface.attributes.alias)
        or interfaces.render_mac_address(interface.attributes.phys_address)
    )

    return InterfaceInv(
        index=interface.attributes.index,
        descr=interface.attributes.descr,
        alias=interface.attributes.alias,
        type=interface.attributes.type,
        speed=int(interface.attributes.speed),
        oper_status=int(interface.attributes.oper_status),
        phys_address=mac,
        bond=bond_map.get(mac),
    )


def inventory_lnx_if(
    section_lnx_if: Section | None,
    section_bonding: bonding.Section | None,
) -> InventoryResult:
    if section_lnx_if is None:
        return

    ifaces, ip_stats = section_lnx_if

    mac_map = bonding.get_mac_map(section_bonding) if section_bonding else {}
    bond_map = bonding.get_bond_map(section_bonding) if section_bonding else {}

    yield from inventorize_interfaces(
        {
            "usage_port_types": [
                "6",
                "32",
                "62",
                "117",
                "127",
                "128",
                "129",
                "180",
                "181",
                "182",
                "205",
                "229",
            ],
        },
        (
            inv_if
            for interface in ifaces
            if (inv_if := _make_inventory_interface(interface, mac_map, bond_map)) is not None
        ),
        len(ifaces),
    )

    yield from _inventorize_addresses(ip_stats)


def _inventorize_addresses(ip_stats: SectionInventory) -> InventoryResult:
    for if_name, interface in ip_stats.items():
        for networks, ty in [
            (interface.inet, "ipv4"),
            (interface.inet6, "ipv6"),
        ]:
            for network in networks:
                yield TableRow(
                    path=["networking", "addresses"],
                    key_columns={
                        "device": if_name,
                        "address": _get_address(network),
                    },
                    inventory_columns={
                        "type": ty,
                    },
                )


def _get_address(network: str) -> str:
    return network.split("/")[0]


inventory_plugin_lnx_if = InventoryPlugin(
    name="lnx_if",
    sections=["lnx_if", "bonding"],
    inventory_function=inventory_lnx_if,
    # TODO Use inv_if? Also have a look at winperf_if and other interface intentories..
    # inventory_ruleset_name="inv_if",
    # inventory_default_parameters={},
)
