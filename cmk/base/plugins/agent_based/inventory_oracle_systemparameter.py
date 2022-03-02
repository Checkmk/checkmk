#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<oracle_systemparameter:sep(124)>>>
# XE|lock_name_space||TRUE
# XE|processes|100|TRUE
# XE|sessions|172|FALSE

from typing import Dict, List, Mapping, Sequence

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

Section = Mapping[str, Sequence[Mapping[str, str]]]


def parse_oracle_systemparameter(string_table: StringTable) -> Section:
    parsed: Dict[str, List[Mapping[str, str]]] = {}

    for line in string_table:
        if len(line) != 4:
            continue

        sid, param_name, value, isdefault = line
        parsed.setdefault(sid, []).append(
            {
                "param_name": param_name,
                "value": value,
                "isdefault": isdefault,
            }
        )
    return parsed


register.agent_section(
    name="oracle_systemparameter",
    parse_function=parse_oracle_systemparameter,
)


def inventory_oracle_systemparameter(section: Section) -> InventoryResult:
    path = ["software", "applications", "oracle", "systemparameter"]
    for inst, data in section.items():
        for param in data:
            param_name = param["param_name"]

            # Add here specific V$SYSTEMPARAMETERS which should not be tracked in the Inventory History
            # (e.g. because they are changing often)
            vsys_params_to_exclude = {"resource_manager_plan"}
            if param_name in vsys_params_to_exclude:
                continue

            yield TableRow(
                path=path,
                key_columns={
                    "sid": inst,
                    "name": param_name,
                },
                inventory_columns={
                    "value": param["value"],
                    "isdefault": param["isdefault"],
                },
                status_columns={},
            )


register.inventory_plugin(
    name="oracle_systemparameter",
    inventory_function=inventory_oracle_systemparameter,
)
