#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils.checkmk import ControllerSection


def parse_cmk_agent_ctl_status(string_table: StringTable) -> Optional[ControllerSection]:
    try:
        json_str = string_table[0][0]
    except IndexError:
        return None

    return ControllerSection.parse_raw(json_str)


register.agent_section(
    name="cmk_agent_ctl_status",
    parse_function=parse_cmk_agent_ctl_status,
)
