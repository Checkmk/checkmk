#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

from .agent_based_api.v1 import register
from .utils.threepar import parse_3par


@dataclass
class ThreeParSystem:
    name: str | None
    serial_number: str
    model: str
    system_version: str
    cluster_nodes: Sequence[int]
    online_nodes: Sequence[int]


def parse_3par_system(string_table: StringTable) -> ThreeParSystem:
    pre_parsed = parse_3par(string_table)

    return ThreeParSystem(
        name=pre_parsed.get("name"),
        serial_number=pre_parsed.get("serialNumber", "N/A"),
        model=pre_parsed.get("model", "N/A"),
        system_version=pre_parsed.get("systemVersion", "N/A"),
        cluster_nodes=pre_parsed.get("clusterNodes", []),
        online_nodes=pre_parsed.get("onlineNodes", []),
    )


register.agent_section(
    name="3par_system",
    parse_function=parse_3par_system,
)
