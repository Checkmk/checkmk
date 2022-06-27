#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple

from .agent_based_api.v1 import Attributes, register
from .agent_based_api.v1.type_defs import InventoryResult, StringTable


class Section(NamedTuple):
    version: str


def parse_aix_baselevel(string_table: StringTable) -> Section:
    return Section(string_table[0][0])


register.agent_section(
    name="aix_baselevel",
    parse_function=parse_aix_baselevel,
)


def inventory_aix_baselevel(section: Section) -> InventoryResult:
    yield Attributes(
        path=["software", "os"],
        inventory_attributes={
            "version": section.version,
            "vendor": "IBM",
            "type": "aix",
            "name": f"IBM AIX {section.version}",
        },
    )


register.inventory_plugin(
    name="aix_baselevel",
    inventory_function=inventory_aix_baselevel,
)
