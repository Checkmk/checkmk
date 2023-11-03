#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils import robotmk_api


def parse(string_table: StringTable) -> robotmk_api.Section:
    return robotmk_api.parse(string_table)


register.agent_section(
    name="robotmk_v2",
    parse_function=parse,
)
