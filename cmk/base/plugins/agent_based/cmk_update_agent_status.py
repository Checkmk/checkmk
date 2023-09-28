#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils.checkmk import CMKAgentUpdateSection


def _parse_cmk_update_agent_status(string_table: StringTable) -> CMKAgentUpdateSection | None:
    """parse cmk_update_agent_status"""

    try:
        return CMKAgentUpdateSection.parse_raw(string_table[0][0])
    except IndexError:
        return None


register.agent_section(
    name="cmk_update_agent_status",
    parse_function=_parse_cmk_update_agent_status,
)
