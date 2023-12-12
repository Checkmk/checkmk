#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.juniper_mem import (
    check_juniper_mem_generic,
    discover_juniper_mem_generic,
    Section,
)
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree
from cmk.agent_based.v2.type_defs import StringTable
from cmk.plugins.lib.juniper import DETECT_JUNIPER_TRPZ


def parse_juniper_trpz_mem(string_table: StringTable) -> Section | None:
    return (
        Section(int(string_table[0][0]) * 1024, int(string_table[0][1]) * 1024)
        if string_table
        else None
    )


check_info["juniper_trpz_mem"] = LegacyCheckDefinition(
    detect=DETECT_JUNIPER_TRPZ,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14525.4.8.1.1",
        oids=["12.1", "6"],
    ),
    service_name="Memory",
    parse_function=parse_juniper_trpz_mem,
    discovery_function=discover_juniper_mem_generic,
    check_function=check_juniper_mem_generic,
    check_ruleset_name="juniper_mem",
    check_default_parameters={
        "levels": ("perc_used", (80.0, 90.0)),
    },
)
