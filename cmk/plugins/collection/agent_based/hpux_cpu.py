#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import AgentSection, StringTable
from cmk.plugins.lib.cpu import Load, Section


def parse_hpux_cpu(string_table: StringTable) -> Section | None:
    return (
        Section(
            load=Load(*(float(l.strip(",")) for l in string_table[0][-3:])),
            num_cpus=int(string_table[1][0]) if len(string_table) > 1 else 1,
        )
        if string_table and "load" in string_table[0]
        else None
    )


agent_section_hpux_cpu = AgentSection(
    name="hpux_cpu",
    parsed_section_name="cpu",
    parse_function=parse_hpux_cpu,
)
