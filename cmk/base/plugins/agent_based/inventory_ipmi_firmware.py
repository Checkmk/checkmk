#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping

from .agent_based_api.v1 import Attributes, register
from .agent_based_api.v1.type_defs import StringTable

Section = Mapping[str, str]


def parse_ipmi_firmware(string_table: StringTable) -> Section:
    section = {"type": "IPMI"}

    for line in string_table:
        if line[0] == "BMC Version" and line[1] == "version":
            section["version"] = line[2]

    return section


register.agent_section(
    name="ipmi_firmware",
    parse_function=parse_ipmi_firmware,
)


def inventory_ipmi_firmware(section: Section):
    yield Attributes(
        path=["hardware", "management_interface"],
        inventory_attributes=section,
    )


register.inventory_plugin(
    name="ipmi_firmware",
    inventory_function=inventory_ipmi_firmware,
)
