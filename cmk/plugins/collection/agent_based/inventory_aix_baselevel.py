#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple

from cmk.agent_based.v2 import (
    AgentSection,
    Attributes,
    InventoryPlugin,
    InventoryResult,
    StringTable,
)


class Section(NamedTuple):
    version: str


def parse_aix_baselevel(string_table: StringTable) -> Section:
    return Section(string_table[0][0])


agent_section_aix_baselevel = AgentSection(
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


inventory_plugin_aix_baselevel = InventoryPlugin(
    name="aix_baselevel",
    inventory_function=inventory_aix_baselevel,
)
