#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping

from .agent_based_api.v1 import Attributes, register
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

Section = Mapping[str, str]


def parse_solaris_uname(string_table: StringTable) -> Section:
    return {k.strip(): v.strip() for k, v in string_table}


register.agent_section(
    name="solaris_uname",
    parse_function=parse_solaris_uname,
)


def inventory_solaris_uname(section: Section) -> InventoryResult:
    yield Attributes(
        path=["software", "os"],
        inventory_attributes={
            "vendor": "Oracle",
            "type": section["System"],
            "version": section["Release"],
            "name": "%s %s" % (section["System"], section["Release"]),
            "kernel_version": section["KernelID"],
            "hostname": section["Node"],
        },
    )


register.inventory_plugin(
    name="solaris_uname",
    inventory_function=inventory_solaris_uname,
)
