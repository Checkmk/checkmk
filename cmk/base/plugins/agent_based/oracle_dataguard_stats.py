#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, Mapping

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

Section = Mapping[str, Mapping[str, Any]]


def parse_oracle_dataguard_stats(string_table: StringTable) -> Section:
    parsed: Dict[str, Dict[str, Any]] = {}
    for line in string_table:
        instance = {}
        if len(line) >= 5:
            db_name, db_unique_name, database_role, dgstat_parm, dgstat_value = line[:5]
            instance = parsed.setdefault(
                "%s.%s" % (db_name, db_unique_name),
                {
                    "database_role": database_role,
                    "dgstat": {},
                },
            )
            instance["dgstat"][dgstat_parm] = dgstat_value

        if len(line) >= 6:
            # new plugin output with switchover_status
            instance["switchover_status"] = line[5]

        if len(line) >= 13:
            # new format for Broker and Observer information
            instance.update(
                {
                    "broker_state": line[6],
                    "protection_mode": line[7],
                    "fs_failover_status": line[8],
                    "fs_failover_observer_present": line[9],
                    "fs_failover_observer_host": line[10],
                    "fs_failover_target": line[11],
                    "mrp_status": line[12],
                }
            )
        if len(line) >= 14:
            # new format with open_mode
            instance.update(
                {
                    "broker_state": line[6],
                    "protection_mode": line[7],
                    "fs_failover_status": line[8],
                    "fs_failover_observer_present": line[9],
                    "fs_failover_observer_host": line[10],
                    "fs_failover_target": line[11],
                    "mrp_status": line[12],
                    "open_mode": line[13],
                }
            )

    return parsed


register.agent_section(
    name="oracle_dataguard_stats",
    parse_function=parse_oracle_dataguard_stats,
)


def inventory_oracle_dataguard_stats(section: Section) -> InventoryResult:
    path = ["software", "applications", "oracle", "dataguard_stats"]
    for inst, data in section.items():
        try:
            db_name, db_unique_name = inst.split(".", 1)
        except ValueError:
            continue

        yield TableRow(
            path=path,
            key_columns={
                "sid": db_name,
                "db_unique": "%s.%s" % (db_name, db_unique_name),
            },
            inventory_columns={
                "role": data.get("database_role"),
                "switchover": data.get("switchover_status"),
            },
            status_columns={},
        )


register.inventory_plugin(
    name="oracle_dataguard_stats",
    inventory_function=inventory_oracle_dataguard_stats,
)
