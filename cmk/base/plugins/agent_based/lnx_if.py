#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple, Union

from .agent_based_api.v1 import register, TableRow, type_defs
from .agent_based_api.v1.type_defs import InventoryResult
from .utils import interfaces
from .utils.inventory_interfaces import Interface as InterfaceInv
from .utils.inventory_interfaces import inventorize_interfaces

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

SectionInventory = Dict[str, Dict[str, Union[str, Sequence[str]]]]
Section = Tuple[interfaces.Section, SectionInventory]


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
            iface = ip_stats.setdefault(line[1][:-1].split("@")[0], {})
            # The interface flags are summarized in the angle brackets.
            iface["state_infos"] = line[2][1:-1].split(",")
            continue

        if not iface:
            continue

        if line[0].startswith("link/"):
            # link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
            # link/none
            try:
                iface[line[0]] = line[1]
                iface[line[2]] = line[3]
            except IndexError:
                pass

        elif line[0].startswith("inet"):
            if "temporary" in line and "dynamic" in line:
                continue
            # inet 127.0.0.1/8 scope host lo
            # inet6 ::1/128 scope host
            inet_data = iface.setdefault(line[0], [])
            assert isinstance(inet_data, list)
            inet_data.append(line[1])
    return ip_stats


def _parse_lnx_if_sections(string_table: type_defs.StringTable):
    ip_stats = {}
    ethtool_stats: Dict[str, Dict[str, Union[str, int, Sequence[int]]]] = {}
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
            iface = ethtool_stats.setdefault(line[0], {})
            iface.update({"counters": list(map(int, line[1].strip().split()))})
            continue

        elif line[0].startswith("[") and line[0].endswith("]"):
            # Parse 'ethtool' output
            # [IF_NAME]
            #       KEY: VAL
            #       KEY: VAL
            #       ...
            iface = ethtool_stats.setdefault(line[0][1:-1], {})
            ethtool_index += 1
            iface["ethtool_index"] = ethtool_index
            continue

        if iface is not None:
            stripped_line0 = line[0].strip()
            if stripped_line0 == "Address":
                iface[stripped_line0] = ":".join(line[1:]).strip()
            else:
                iface[stripped_line0] = " ".join(line[1:]).strip()
    return ip_stats, ethtool_stats


def parse_lnx_if(string_table: type_defs.StringTable) -> Section:
    ip_stats, ethtool_stats = _parse_lnx_if_sections(string_table)

    nic_info = []
    for iface_name, iface in sorted(ethtool_stats.items()):
        iface.update(ip_stats.get(iface_name, {}))
        nic_info.append((iface_name, iface))

    if_table = []
    for index, (nic, attr) in enumerate(nic_info):
        counters = attr.get("counters", [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        ifIndex = attr.get("ethtool_index", index + 1)
        ifDescr = nic
        ifAlias = nic

        # Guess type from name of interface
        if nic == "lo":
            ifType = 24
        else:
            ifType = 6

        # Compute speed
        speed_text = attr.get("Speed")
        if speed_text is None:
            ifSpeed = 0
        else:
            if speed_text == "65535Mb/s":  # unknown
                ifSpeed = 0
            elif speed_text.endswith("Kb/s"):
                ifSpeed = int(float(speed_text[:-4])) * 1000
            elif speed_text.endswith("Mb/s"):
                ifSpeed = int(float(speed_text[:-4])) * 1000000
            elif speed_text.endswith("Gb/s"):
                ifSpeed = int(float(speed_text[:-4])) * 1000000000
            else:
                ifSpeed = 0

        # Performance counters
        ifInOctets = counters[0]
        inucast = counters[1] + counters[7]
        inmcast = counters[7]
        inbcast = 0
        ifInDiscards = counters[3]
        ifInErrors = counters[2]
        ifOutOctets = counters[8]
        outucast = counters[9]
        outmcast = 0
        outbcast = 0
        ifOutDiscards = counters[11]
        ifOutErrors = counters[10]
        ifOutQLen = counters[12]

        # Link state from ethtool. If ethtool has no information about
        # this NIC, we set the state to unknown.
        ld = attr.get("Link detected")
        if ld == "yes":
            ifOperStatus = 1
        elif ld == "no":
            ifOperStatus = 2
        else:
            # No information from ethtool. We consider interfaces up
            # if they have been used at least some time since the
            # system boot.
            state_infos = attr.get("state_infos")
            if state_infos is None:
                if ifInOctets > 0:
                    ifOperStatus = 1  # assume up
                else:
                    ifOperStatus = 4  # unknown (NIC has never been used)
            else:
                # Assumption:
                # abc: <BROADCAST,MULTICAST,UP,LOWER_UP>    UP + LOWER_UP   => really UP
                # def: <NO-CARRIER,BROADCAST,MULTICAST,UP>  NO-CARRIER + UP => DOWN, but admin UP
                # ghi: <BROADCAST,MULTICAST>                unconfigured    => DOWN
                if "UP" in state_infos and "LOWER_UP" in state_infos:
                    ifOperStatus = 1
                else:
                    ifOperStatus = 2

        raw_phys_address = attr.get("Address", attr.get("link/ether", ""))
        if ":" in raw_phys_address:
            # We saw interface entries of tunnels for the address
            # is an integer, eg. '1910236'; especially on OpenBSD.
            ifPhysAddress = interfaces.mac_address_from_hexstring(raw_phys_address)
        else:
            ifPhysAddress = ""

        if_table.append(
            interfaces.Interface(
                index=str(ifIndex),
                descr=str(ifDescr),
                type=str(ifType),
                speed=ifSpeed,
                oper_status=str(ifOperStatus),
                in_octets=ifInOctets,
                in_ucast=inucast,
                in_mcast=inmcast,
                in_bcast=inbcast,
                in_discards=ifInDiscards,
                in_errors=ifInErrors,
                out_octets=ifOutOctets,
                out_ucast=outucast,
                out_mcast=outmcast,
                out_bcast=outbcast,
                out_discards=ifOutDiscards,
                out_errors=ifOutErrors,
                out_qlen=ifOutQLen,
                alias=ifAlias,
                phys_address=ifPhysAddress,
            )
        )

    return if_table, ip_stats


register.agent_section(
    name="lnx_if",
    parse_function=parse_lnx_if,
    supersedes=["if", "if64"],
)


def discover_lnx_if(
    params: Sequence[Mapping[str, Any]],
    section: Section,
) -> type_defs.DiscoveryResult:
    # Always exclude dockers veth* interfaces on docker nodes
    if_table = [iface for iface in section[0] if not iface.descr.startswith("veth")]
    yield from interfaces.discover_interfaces(
        params,
        if_table,
    )


def check_lnx_if(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> type_defs.CheckResult:
    yield from interfaces.check_multiple_interfaces(
        item,
        params,
        section[0],
    )


def cluster_check_lnx_if(
    item: str,
    params: Mapping[str, Any],
    section: Mapping[str, Optional[Section]],
) -> type_defs.CheckResult:
    yield from interfaces.cluster_check(
        item,
        params,
        {
            node: node_section[0]
            for node, node_section in section.items()
            if node_section is not None
        },
    )


register.check_plugin(
    name="lnx_if",
    service_name="Interface %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=discover_lnx_if,
    check_ruleset_name="if",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=check_lnx_if,
    cluster_check_function=cluster_check_lnx_if,
)


def _make_inventory_interface(interface: interfaces.Interface) -> Optional[InterfaceInv]:
    # Always exclude dockers veth* interfaces on docker nodes.
    # Useless entries for "TenGigabitEthernet2/1/21--Uncontrolled".
    # Ignore useless half-empty tables (e.g. Viprinet-Router).
    if interface.descr.startswith("veth") or interface.type in ("231", "232"):
        return None

    return InterfaceInv(
        index=interface.index,
        descr=interface.descr,
        alias=interface.alias,
        type=interface.type,
        speed=int(interface.speed),
        oper_status=int(interface.oper_status),
        phys_address=interfaces.render_mac_address(interface.phys_address),
    )


def inventory_lnx_if(section: Section) -> InventoryResult:
    ifaces, ip_stats = section

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
            if (inv_if := _make_inventory_interface(interface)) is not None
        ),
        len(ifaces),
    )

    yield from _inventorize_addresses(ip_stats)


def _inventorize_addresses(ip_stats: Mapping[str, Mapping[str, Any]]) -> InventoryResult:
    for if_name, attrs in ip_stats.items():
        for key, ty in [
            ("inet", "ipv4"),
            ("inet6", "ipv6"),
        ]:
            for network in attrs.get(key, []):
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


register.inventory_plugin(
    name="lnx_if",
    inventory_function=inventory_lnx_if,
    # TODO Use inv_if? Also have a look at winperf_if and other interface intentories..
    # inventory_ruleset_name="inv_if",
    # inventory_default_parameters={},
)
