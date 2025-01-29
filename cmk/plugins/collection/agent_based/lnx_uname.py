#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    Attributes,
    InventoryPlugin,
    InventoryResult,
    StringTable,
)


def parse_lnx_uname(string_table: StringTable) -> Mapping[str, str]:
    return {k: line[0] for k, line in zip(["arch", "kernel_version"], string_table)}


agent_section_lnx_uname = AgentSection(
    name="lnx_uname",
    parse_function=parse_lnx_uname,
)


def inventory_lnx_uname(section: Mapping[str, str]) -> InventoryResult:
    yield Attributes(path=["software", "os"], inventory_attributes=section)


inventory_plugin_lnx_uname = InventoryPlugin(
    name="lnx_uname",
    inventory_function=inventory_lnx_uname,
)
