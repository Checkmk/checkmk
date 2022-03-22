#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, TypedDict


class Interface(TypedDict, total=False):
    status: str
    mode: str
    hwaddr: str
    failures: int
    aggregator_id: str


class Bond(TypedDict, total=False):
    status: str
    speed: str
    mode: str
    interfaces: Mapping[str, Interface]
    aggregator_id: str
    active: str
    primary: str


Section = Mapping[str, Bond]


def get_mac_map(section: Section) -> Mapping[str, str]:
    """Map interface names to the MAC addresses

    Bonded interfaces are assigned a new MAC adresses in some outputs.
    This map is used to look up the original one.
    """
    return {
        if_name: mac
        for bond in section.values()
        for if_name, interface in bond.get("interfaces", {}).items()
        if (mac := interface.get("hwaddr"))
    }


def get_bond_map(section: Section) -> Mapping[str, str]:
    """Map interfaces by MAC to the bond they're part of"""
    return {
        mac: bond_name
        for bond_name, bond in section.items()
        for interface in bond.get("interfaces", {}).values()
        if (mac := interface.get("hwaddr"))
    }
