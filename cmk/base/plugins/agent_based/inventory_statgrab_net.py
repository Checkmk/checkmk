#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Sequence

from .agent_based_api.v1 import register, type_defs
from .agent_based_api.v1.type_defs import InventoryResult
from .utils import interfaces
from .utils.inventory_interfaces import Interface as InterfaceInv
from .utils.inventory_interfaces import inventorize_interfaces

Section = Sequence[interfaces.InterfaceWithCounters]


def parse_statgrab_net(string_table: type_defs.StringTable) -> Section:
    nics: Dict[str, Dict[str, str]] = {}
    for nic_varname, value in string_table:
        nic_id, varname = nic_varname.split(".")
        nics.setdefault(nic_id, {})[varname] = value

    return [
        interfaces.InterfaceWithCounters(
            interfaces.Attributes(
                index=str(nr + 1),
                descr=nic_id,
                alias=nic.get("interface_name", nic_id),
                type=nic_id.startswith("lo") and "24" or "6",
                speed=int(nic.get("speed", 0)) * 1000000,
                oper_status=nic.get("up") == "true" and "1" or "2",
            ),
            interfaces.Counters(
                in_octets=interfaces.saveint(nic.get("rx", 0)),
                in_ucast=interfaces.saveint(nic.get("ipackets", 0)),
                in_err=interfaces.saveint(nic.get("ierrors", 0)),
                out_octets=interfaces.saveint(nic.get("tx", 0)),
                out_ucast=interfaces.saveint(nic.get("opackets", 0)),
                out_disc=interfaces.saveint(nic.get("collisions", 0)),
                out_err=interfaces.saveint(nic.get("oerrors", 0)),
            ),
        )
        for nr, (nic_id, nic) in enumerate(nics.items())
    ]


register.agent_section(
    name="statgrab_net",
    parse_function=parse_statgrab_net,
    parsed_section_name="interfaces",
)


def inventory_statgrab_net(section: Section) -> InventoryResult:
    if not section:
        return

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
            InterfaceInv(
                index=interface.attributes.index,
                descr=interface.attributes.descr,
                alias=interface.attributes.alias,
                type=interface.attributes.type,
                speed=int(interface.attributes.speed),
                oper_status=int(interface.attributes.oper_status)
                if isinstance(interface.attributes.oper_status, str)
                else None,
                phys_address=interfaces.render_mac_address(interface.attributes.phys_address),
            )
            for interface in sorted(section, key=lambda i: i.attributes.index)
            if interface.attributes.speed
        ),
        len(section),
    )


register.inventory_plugin(
    name="statgrab_net",
    inventory_function=inventory_statgrab_net,
    # TODO use 'inv_if'
    # inventory_ruleset_name="inv_if",
    # inventory_default_parameters={},
)
