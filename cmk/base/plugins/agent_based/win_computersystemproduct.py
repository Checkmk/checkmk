#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from dataclasses import asdict, dataclass

from .agent_based_api.v1 import Attributes, register
from .agent_based_api.v1.type_defs import InventoryResult, StringTable


@dataclass
class _Section:
    uuid: str


def parse_win_computersystemproduct(string_table: StringTable) -> _Section | None:
    raw_section = {k.lower(): " ".join(v).strip() for k, *v in string_table}
    if "uuid" not in raw_section:
        return None
    return _Section(
        uuid=raw_section["uuid"],
    )


register.agent_section(
    name="win_computersystemproduct",
    parse_function=parse_win_computersystemproduct,
)


def inventory_win_computersystemproduct(section: _Section | None) -> InventoryResult:
    if section is not None:
        yield Attributes(
            path=["hardware", "system"],
            inventory_attributes=asdict(section),
        )


register.inventory_plugin(
    name="win_computersystemproduct",
    inventory_function=inventory_win_computersystemproduct,
)
