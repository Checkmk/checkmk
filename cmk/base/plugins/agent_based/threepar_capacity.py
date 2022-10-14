#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

from .agent_based_api.v1 import register
from .utils.threepar import parse_3par


@dataclass
class ThreeParCapacity:
    name: str
    total_capacity: int
    free_capacity: int
    failed_capacity: int


ThreeParCapacitySection = Mapping[str, ThreeParCapacity]


def parse_threepar_capacity(string_table: StringTable) -> ThreeParCapacitySection:

    return {
        raw_name.replace("Capacity", ""): ThreeParCapacity(
            name=raw_name.replace("Capacity", ""),
            total_capacity=raw_values["totalMiB"],
            free_capacity=raw_values["freeMiB"],
            failed_capacity=raw_values["failedCapacityMiB"],
        )
        for raw_name, raw_values in parse_3par(string_table).items()
    }


register.agent_section(
    name="3par_capacity",
    parse_function=parse_threepar_capacity,
)
