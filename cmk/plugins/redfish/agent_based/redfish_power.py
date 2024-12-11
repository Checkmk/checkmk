#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-

# (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>

# License: GNU General Public License v2

from cmk.agent_based.v2 import AgentSection
from cmk.plugins.redfish.lib import (
    parse_redfish_multiple,
)

agent_section_redfish_power = AgentSection(
    name="redfish_power",
    parse_function=parse_redfish_multiple,
    parsed_section_name="redfish_power",
)
