#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict

from .agent_based_api.v1 import register, type_defs
from .agent_based_api.v1.type_defs import InventoryResult
from .utils import interfaces
from .utils.inventory_interfaces import Interface as InterfaceInv
from .utils.inventory_interfaces import inventorize_interfaces


def parse_statgrab_net(string_table: type_defs.StringTable) -> interfaces.Section:
    nics: Dict[str, Dict[str, str]] = {}
    for nic_varname, value in string_table:
        nic_id, varname = nic_varname.split(".")
        nics.setdefault(nic_id, {})[varname] = value

    return [
        interfaces.Interface(
            index=str(nr + 1),
            descr=nic_id,
            alias=nic.get("interface_name", nic_id),
            type=nic_id.startswith("lo") and "24" or "6",
            speed=int(nic.get("speed", 0)) * 1000000,
            oper_status=nic.get("up") == "true" and "1" or "2",
            in_octets=interfaces.saveint(nic.get("rx", 0)),
            in_ucast=interfaces.saveint(nic.get("ipackets", 0)),
            in_errors=interfaces.saveint(nic.get("ierrors", 0)),
            out_octets=interfaces.saveint(nic.get("tx", 0)),
            out_ucast=interfaces.saveint(nic.get("opackets", 0)),
            out_discards=interfaces.saveint(nic.get("collisions", 0)),
            out_errors=interfaces.saveint(nic.get("oerrors", 0)),
        )
        for nr, (nic_id, nic) in enumerate(nics.items())
    ]


register.agent_section(
    name="statgrab_net",
    parse_function=parse_statgrab_net,
    parsed_section_name="interfaces",
)


def inventory_statgrab_net(section: interfaces.Section) -> InventoryResult:
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
                index=interface.index,
                descr=interface.descr,
                alias=interface.alias,
                type=interface.type,
                speed=int(interface.speed),
                oper_status=int(interface.oper_status),
                phys_address=interfaces.render_mac_address(interface.phys_address),
            )
            for interface in sorted(section, key=lambda i: i.index)
            if interface.speed
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
