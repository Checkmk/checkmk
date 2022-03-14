#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

Section = StringTable


def inventory_oracle_recovery_area(section: Section) -> InventoryResult:
    for line in section:
        yield TableRow(
            path=["software", "applications", "oracle", "recovery_area"],
            key_columns={
                "sid": line[0],
            },
            inventory_columns={
                "flashback": line[-1],
            },
            status_columns={},
        )


register.inventory_plugin(
    name="oracle_recovery_area",
    inventory_function=inventory_oracle_recovery_area,
)
