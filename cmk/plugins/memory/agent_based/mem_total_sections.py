#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re

from cmk.agent_based.v2 import AgentSection, StringTable
from cmk.plugins.lib.memory import SectionMemTotal

# mem_total is used in conjunction with the ps check that can be configured to
# check the relative ram usage, so it has to know how much memory is available
# on the system


def parse_mem_total_solaris(string_table: StringTable) -> SectionMemTotal:
    if match := re.match(r"Memory size: (\d+) Megabytes", string_table[0][0]):
        return SectionMemTotal(int(match.groups()[0]) * 1024 * 1024)
    raise ValueError(f"parse_statgrab_mem: can not parse {string_table!r}")


agent_section_mem_total_solaris = AgentSection(
    name="mem_total_solaris",
    parsed_section_name="mem_total",
    parse_function=parse_mem_total_solaris,
)
