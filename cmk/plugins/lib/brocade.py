#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import all_of, exists, startswith

DETECT = all_of(
    startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1588.2.1.1"),
    exists(".1.3.6.1.4.1.1588.2.1.1.1.6.2.1.*"),
)

DETECT_MLX = startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1991.1.")


DISCOVERY_DEFAULT_PARAMETERS = {
    "admstates": [1, 3, 4],
    "phystates": [3, 4, 5, 6, 7, 8, 9, 10],
    "opstates": [1, 2, 3, 4],
    "use_portname": True,
    "show_isl": True,
}


def brocade_fcport_inventory_this_port(
    admstate: int,
    phystate: int,
    opstate: int,
    settings: Mapping[str, list[int]],
) -> bool:
    if admstate not in settings["admstates"]:
        return False
    if phystate not in settings["phystates"]:
        return False
    return opstate in settings["opstates"]


def brocade_fcport_getitem(
    number_of_ports: int,
    index: int,
    portname: str,
    is_isl: bool,
    settings: Mapping[str, bool],
) -> str:
    itemname = ("%0" + str(len(str(number_of_ports))) + "d") % (index - 1)
    if is_isl and settings["show_isl"]:
        itemname += " ISL"
    if portname.strip() and settings["use_portname"]:
        itemname += " " + portname.strip()
    return itemname
