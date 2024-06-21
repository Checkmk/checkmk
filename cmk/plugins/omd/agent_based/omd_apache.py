#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import AgentSection, StringTable

_Section = Mapping[str, StringTable]


def parse_omd_apache(string_table: StringTable) -> _Section:
    parsed: dict[str, StringTable] = {}
    site = None
    for line in string_table:
        if line[0][0] == "[":
            site = line[0][1:-1]
            parsed[site] = []
        elif site:
            parsed[site].append(line)
    return parsed


agent_section_omd_apache = AgentSection(
    name="omd_apache",
    parse_function=parse_omd_apache,
)
