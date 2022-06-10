#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping

from .agent_based_api.v1 import Attributes, register
from .agent_based_api.v1.type_defs import InventoryResult, StringTable


def parse_lnx_uname(string_table: StringTable) -> Mapping[str, str]:
    return {k: line[0] for k, line in zip(["arch", "kernel_version"], string_table)}


register.agent_section(
    name="lnx_uname",
    parse_function=parse_lnx_uname,
)


def inventory_lnx_uname(section: Mapping[str, str]) -> InventoryResult:
    yield Attributes(path=["software", "os"], inventory_attributes=section)


register.inventory_plugin(
    name="lnx_uname",
    inventory_function=inventory_lnx_uname,
)
