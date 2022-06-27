#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from dataclasses import asdict, dataclass

from .agent_based_api.v1 import Attributes, register
from .agent_based_api.v1.type_defs import InventoryResult, StringTable


@dataclass
class _Section:
    manufacturer: str
    model: str
    family: str


def parse_win_computersystem(string_table: StringTable) -> _Section:
    raw_section = {k.lower(): " ".join(v).strip() for k, *v in string_table}
    return _Section(
        manufacturer=raw_section["manufacturer"],
        model=raw_section["model"],
        family=raw_section["name"],
    )


register.agent_section(
    name="win_computersystem",
    parse_function=parse_win_computersystem,
)


def inventory_win_computersystem(section: _Section) -> InventoryResult:
    yield Attributes(
        path=["hardware", "system"],
        inventory_attributes=asdict(section),
    )


register.inventory_plugin(
    name="win_computersystem",
    inventory_function=inventory_win_computersystem,
)
