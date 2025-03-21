#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# -- (type|target|mask|gateway|device)
# <<<win_ip_r:sep(124):persist(1495544240)>>>
# indirect|0.0.0.0|0.0.0.0|11.112.81.1|vmxnet3 Ethernet Adapter #2
# direct|11.112.81.0|255.255.255.0|0.0.0.0|vmxnet3 Ethernet Adapter #2
# direct|11.112.81.34|255.255.255.255|0.0.0.0|vmxnet3 Ethernet Adapter #2
# direct|11.112.81.36|255.255.255.255|0.0.0.0|vmxnet3 Ethernet Adapter #2
# direct|11.112.81.39|255.255.255.255|0.0.0.0|vmxnet3 Ethernet Adapter #2
# direct|11.112.81.41|255.255.255.255|0.0.0.0|vmxnet3 Ethernet Adapter #2
# direct|11.112.81.43|255.255.255.255|0.0.0.0|vmxnet3 Ethernet Adapter #2
# direct|11.112.81.44|255.255.255.255|0.0.0.0|vmxnet3 Ethernet Adapter #2
# direct|11.112.81.45|255.255.255.255|0.0.0.0|vmxnet3 Ethernet Adapter #2
# direct|11.112.81.46|255.255.255.255|0.0.0.0|vmxnet3 Ethernet Adapter #2
# direct|11.112.81.255|255.255.255.255|0.0.0.0|vmxnet3 Ethernet Adapter #2
# direct|11.112.136.0|255.255.252.0|0.0.0.0|vmxnet3 Ethernet Adapter
# direct|11.112.136.112|255.255.255.255|0.0.0.0|vmxnet3 Ethernet Adapter
# direct|11.112.139.255|255.255.255.255|0.0.0.0|vmxnet3 Ethernet Adapter
# direct|169.254.0.0|255.255.0.0|0.0.0.0|Microsoft Failover Cluster Virtual Adapter
# direct|169.254.2.184|255.255.255.255|0.0.0.0|Microsoft Failover Cluster Virtual Adapter
# direct|169.254.255.255|255.255.255.255|0.0.0.0|Microsoft Failover Cluster Virtual Adapter
# direct|224.0.0.0|240.0.0.0|0.0.0.0|vmxnet3 Ethernet Adapter #2
# direct|224.0.0.0|240.0.0.0|0.0.0.0|vmxnet3 Ethernet Adapter
# direct|224.0.0.0|240.0.0.0|0.0.0.0|Microsoft Failover Cluster Virtual Adapter
# direct|255.255.255.255|255.255.255.255|0.0.0.0|vmxnet3 Ethernet Adapter #2
# direct|255.255.255.255|255.255.255.255|0.0.0.0|vmxnet3 Ethernet Adapter
# direct|255.255.255.255|255.255.255.255|0.0.0.0|Microsoft Failover Cluster Virtual Adapter

from collections.abc import Sequence
from typing import NamedTuple

from cmk.agent_based.v2 import AgentSection, InventoryPlugin, InventoryResult, StringTable, TableRow


class Route(NamedTuple):
    target: str
    device: str
    gateway: str
    type_: str


Section = Sequence[Route]


def parse_win_ip_r(string_table: StringTable) -> Section:
    return [
        Route(
            target="{target}/{subnet}".format(
                target=target,
                # Convert subnetmask to CIDR
                subnet=sum(int(x).bit_count() for x in mask.split(".")),
            ),
            device=device,
            gateway=gateway,
            type_=type_,
        )
        for type_, target, mask, gateway, device in string_table
    ]


agent_section_win_ip_r = AgentSection(
    name="win_ip_r",
    parse_function=parse_win_ip_r,
)


def inventory_win_ip_r(section: Section) -> InventoryResult:
    for route in section:
        yield TableRow(
            path=["networking", "routes"],
            key_columns={
                "target": route.target,
                "gateway": route.gateway,
            },
            inventory_columns={
                "device": route.device,
                "type": route.type_,
            },
            status_columns={},
        )


inventory_plugin_win_ip_r = InventoryPlugin(
    name="win_ip_r",
    inventory_function=inventory_win_ip_r,
)
