#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pydantic

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, type_defs
from cmk.base.plugins.agent_based.utils import memory


class MemUsed(pydantic.BaseModel):
    """section: prometheus_mem_used_v1"""

    Cached: int
    MemFree: int
    MemTotal: int
    SwapFree: int
    SwapTotal: int
    Buffers: int
    Dirty: int
    Writeback: int


def parse(string_table: type_defs.StringTable) -> memory.SectionMem:
    """
    >>> parse([['{"Cached": 4213768, "MemFree": 5246232, "MemTotal": 16102284, "SwapFree": 520956, "SwapTotal": 1003516, "Buffers": 237060, "Dirty": 676, "Writeback": 84}']])
    {'Cached': 4213768, 'MemFree': 5246232, 'MemTotal': 16102284, 'SwapFree': 520956, 'SwapTotal': 1003516, 'Buffers': 237060, 'Dirty': 676, 'Writeback': 84}
    """
    parsed_section = MemUsed.parse_raw(string_table[0][0])
    return dict(parsed_section)


register.agent_section(
    name="prometheus_mem_used_v1",
    parse_function=parse,
    parsed_section_name="mem_used",
)
