#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple

from cmk.agent_based.v2 import (
    InventoryPlugin,
    InventoryResult,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
    TableRow,
)
from cmk.plugins.lib import checkpoint


class VPNTunnel(NamedTuple):
    idx: int
    peer_ip: str
    source_ip: str
    peer_name: str
    tunnel_interface: str
    link_priority: str


Section = list[VPNTunnel]


def parse_checkpoint_vpn_tunnels(string_table: StringTable) -> Section:
    link_priorities = {
        "0": "Primary",
        "1": "Backup",
        "2": "On-demand",
    }

    return [
        VPNTunnel(
            idx=index + 1,
            peer_ip=peer_ip,
            source_ip=source_ip,
            peer_name=peer_name,
            tunnel_interface=tunnel_interface,
            link_priority=link_priorities[link_priority],
        )
        for index, (peer_ip, source_ip, peer_name, tunnel_interface, link_priority) in enumerate(
            string_table
        )
    ]


snmp_section_checkpoint_vpn_tunnels = SimpleSNMPSection(
    name="checkpoint_vpn_tunnels",
    parse_function=parse_checkpoint_vpn_tunnels,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.500.9002.1",
        oids=[
            "1",  # tunnelPeerIpAddr
            "7",  # tunnelSourceIpAddr
            "2",  # tunnelPeerObjName
            "6",  # tunnelInterface
            "8",  # tunnelLinkPriority
        ],
    ),
    detect=checkpoint.DETECT,
)


def inventory_checkpoint_vpn_tunnels(section: Section) -> InventoryResult:
    for vpn_tunnel in section:
        yield TableRow(
            path=["networking", "tunnels"],
            key_columns={
                "peername": vpn_tunnel.peer_name,
            },
            inventory_columns={
                "index": vpn_tunnel.idx,
                "peerip": vpn_tunnel.peer_ip,
                "sourceip": vpn_tunnel.source_ip,
                "tunnelinterface": vpn_tunnel.tunnel_interface,
                "linkpriority": vpn_tunnel.link_priority,
            },
        )


inventory_plugin_checkpoint_vpn_tunnels = InventoryPlugin(
    name="checkpoint_vpn_tunnels",
    inventory_function=inventory_checkpoint_vpn_tunnels,
)
