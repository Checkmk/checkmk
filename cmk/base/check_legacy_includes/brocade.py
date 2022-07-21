#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Mapping

from cmk.base.plugins.agent_based.utils import brocade

# This is the variable for the actual rule
brocade_fcport_inventory: list = []


def brocade_fcport_inventory_this_port(
    admstate: int,
    phystate: int,
    opstate: int,
    settings: Mapping[str, list[int]],
) -> bool:
    return brocade.brocade_fcport_inventory_this_port(
        admstate,
        phystate,
        opstate,
        {
            "admstates": [1, 3, 4],
            "phystates": [3, 4, 5, 6, 7, 8, 9, 10],
            "opstates": [1, 2, 3, 4],
            **settings,
        },
    )


def brocade_fcport_getitem(
    number_of_ports: int,
    index: int,
    portname: str,
    is_isl: bool,
    settings: Mapping[str, bool],
) -> str:
    return brocade.brocade_fcport_getitem(
        number_of_ports,
        index,
        portname,
        is_isl,
        {"use_portname": True, "show_isl": True, **settings},
    )
