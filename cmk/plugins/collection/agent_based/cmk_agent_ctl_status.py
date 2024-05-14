#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import AgentSection, StringTable
from cmk.plugins.lib.checkmk import ControllerSection


def parse_cmk_agent_ctl_status(string_table: StringTable) -> ControllerSection | None:
    try:
        json_str = string_table[0][0]
    except IndexError:
        return None

    return ControllerSection.model_validate_json(json_str)


agent_section_cmk_agent_ctl_status = AgentSection(
    name="cmk_agent_ctl_status",
    parse_function=parse_cmk_agent_ctl_status,
)
