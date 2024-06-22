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

Section = Mapping[str, str]


def parse_solaris_uname(string_table: StringTable) -> Section:
    return {k.strip(): v.strip() for k, v in string_table}


agent_section_solaris_uname = AgentSection(
    name="solaris_uname",
    parse_function=parse_solaris_uname,
)


def inventory_solaris_uname(section: Section) -> InventoryResult:
    yield Attributes(
        path=["software", "os"],
        inventory_attributes={
            "vendor": "Oracle",
            "type": section["System"],
            "version": section["Release"],
            "name": "{} {}".format(section["System"], section["Release"]),
            "kernel_version": section["KernelID"],
            "hostname": section["Node"],
        },
    )


inventory_plugin_solaris_uname = InventoryPlugin(
    name="solaris_uname",
    inventory_function=inventory_solaris_uname,
)
