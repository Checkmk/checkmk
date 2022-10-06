#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, MutableMapping
from typing import NamedTuple

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

from .agent_based_api.v1 import register


class VXVMEnclosure(NamedTuple):
    name: str
    status: str


VXVMEnclosureSection = Mapping[str, VXVMEnclosure]


def parse_vxvm_enclosures(string_table: StringTable) -> VXVMEnclosureSection:
    vxvm_enclosures: MutableMapping[str, VXVMEnclosure] = {}

    for line in string_table:
        try:
            name, status = line[0], line[3]
        except IndexError:
            continue

        vxvm_enclosures[name] = VXVMEnclosure(
            name=name,
            status=status,
        )
    return vxvm_enclosures


register.agent_section(
    name="vxvm_enclosures",
    parse_function=parse_vxvm_enclosures,
)
