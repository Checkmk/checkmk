#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output:
# <<<win_system:sep(58)>>>
# Manufacturer : Oracle Corporation
# Name         : Computergehäuse
# Model        :
# HotSwappable :
# InstallDate  :
# PartNumber   :
# SerialNumber :

import dataclasses
import re
from typing import Optional

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable


@dataclasses.dataclass
class Section:
    serial: Optional[str] = None
    manufacturer: Optional[str] = None
    product: Optional[str] = None
    family: Optional[str] = None


def parse(string_table: StringTable) -> Section:
    section = Section()
    for line in string_table:
        if len(line) > 2:
            line = [line[0], ":".join(line[1:])]
        varname, value = line
        varname = re.sub(" *", "", varname)
        value = re.sub("^ ", "", value)
        if varname == "SerialNumber":
            section.serial = value
        elif varname == "Manufacturer":
            section.manufacturer = value
        elif varname == "Name":
            section.product = value
        elif varname == "Model":
            section.family = value
    return section


register.agent_section(
    name="win_system",
    parse_function=parse,
)
