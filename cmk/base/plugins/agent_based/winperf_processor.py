#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Final, List, NamedTuple, Optional
from .agent_based_api.v1.type_defs import StringTable

from .agent_based_api.v1 import register


class CoreTicks(NamedTuple):
    name: str
    total: int
    per_core: List[int]


class Section(NamedTuple):
    time: int
    ticks: List[CoreTicks]


WHAT_MAP: Final = {"-232": "util", "-96": "user", "-94": "privileged"}


def parse_winperf_processor(string_table: StringTable) -> Optional[Section]:
    section = Section(
        time=int(float(string_table[0][0])),
        ticks=[],
    )
    for line in string_table[1:]:
        what = WHAT_MAP.get(line[0])
        if what is None:
            continue
        # behaviour of raising ValueError kept during migration
        section.ticks.append(
            CoreTicks(name=what, total=int(line[-2]), per_core=[int(t) for t in line[1:-2]]))

    return section


register.agent_section(
    name="winperf_processor",
    parse_function=parse_winperf_processor,
)
