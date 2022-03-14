#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, NamedTuple, Optional

from .agent_based_api.v1 import Attributes, register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable


class Section(NamedTuple):
    latest_service_pack: Optional[str]
    service_packs: List[str]


def parse_aix_service_packs(string_table: StringTable) -> Section:
    latest_service_pack = None
    service_packs: List[str] = []
    for line in string_table:
        if line[0].startswith("----") or line[0].startswith("Known"):
            continue
        if latest_service_pack is None:
            latest_service_pack = line[0]
        else:
            service_packs.append(line[0])

    return Section(
        latest_service_pack=latest_service_pack,
        service_packs=service_packs,
    )


register.agent_section(
    name="aix_service_packs",
    parse_function=parse_aix_service_packs,
)


def inventory_aix_service_packs(section: Section) -> InventoryResult:
    yield Attributes(
        path=["software", "os"],
        inventory_attributes={"service_pack": section.latest_service_pack},
    )

    path = ["software", "os", "service_packs"]
    for service_pack in section.service_packs:
        yield TableRow(
            path=path,
            key_columns={"name": service_pack},
        )


register.inventory_plugin(
    name="aix_service_packs",
    inventory_function=inventory_aix_service_packs,
)
