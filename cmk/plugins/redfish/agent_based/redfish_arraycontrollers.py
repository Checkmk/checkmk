#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import AgentSection
from cmk.plugins.redfish.lib import parse_redfish_multiple

agent_section_redfish_arraycontrollers = AgentSection(
    name="redfish_arraycontrollers",
    parse_function=parse_redfish_multiple,
    parsed_section_name="redfish_arraycontrollers",
)
