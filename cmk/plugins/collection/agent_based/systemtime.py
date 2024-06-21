#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import AgentSection, StringTable

Section = Mapping[str, float]


def parse_systemtime(string_table: StringTable) -> Section:
    """
    >>> parse_systemtime([['12345']])
    {'foreign_systemtime': 12345.0}
    >>> parse_systemtime([['12345.2', '567.3']])
    {'foreign_systemtime': 12345.2, 'our_systemtime': 567.3}
    >>> parse_systemtime([[]])
    {}
    """
    return {
        key: float(value)
        for key, value in zip(["foreign_systemtime", "our_systemtime"], string_table[0])
    }


agent_section_systemtime = AgentSection(
    name="systemtime",
    parse_function=parse_systemtime,
)
