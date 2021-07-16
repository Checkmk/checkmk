#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Dict, List, NamedTuple, Optional, Sequence, Union, Mapping

import urllib.parse

from .agent_based_api.v1.type_defs import StringTable
from .agent_based_api.v1 import register

from .utils import cache_helper


class PluginData(NamedTuple):
    name: Optional[str]
    state: int
    info: Sequence[str]
    cache_info: Optional[cache_helper.CacheInfo]


MRPESection = Mapping[str, Sequence[PluginData]]


def parse_mrpe(string_table: StringTable) -> MRPESection:

    parsed: Dict[str, List[PluginData]] = {}
    for line in string_table:

        cache_info = cache_helper.CacheInfo.from_raw(line[0], time.time())
        if cache_info:
            line = line[1:]

        # New Linux agent sends (check_name) in first column. Stay
        # compatible with MRPE versions not providing this info
        if line[0].startswith("("):
            name: Optional[str] = line[0].strip('()')
            line = line[1:]
        else:
            name = None

        if len(line) < 2:
            continue

        item = urllib.parse.unquote(line[0])
        state: Union[str, int] = line[1]
        line = line[2:]

        try:
            state = int(state)
        except ValueError:
            pass

        if state not in (0, 1, 2, 3):
            line.insert(0, "Invalid plugin status '%s'. Output is:" % state)
            state = 3

        # convert to original format by joining and splitting at \1 (which replaced \n)
        text = " ".join(line).split("\1")

        dataset = PluginData(name, int(state), text, cache_info)
        parsed.setdefault(item, []).append(dataset)

    return parsed


register.agent_section(
    name="mrpe",
    parse_function=parse_mrpe,
)
