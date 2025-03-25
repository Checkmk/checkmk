#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import AgentSection, InventoryPlugin, InventoryResult, StringTable, TableRow

Section = Mapping[str, Mapping[str, Any]]

RE_ATTRIBUTES = re.compile(r"[()]")


def parse_ibm_mq_managers(string_table: StringTable) -> Section:
    def get_data_of_line(line):
        splits = RE_ATTRIBUTES.split(line)
        data = {}
        for key, value in zip(splits[::2], splits[1::2]):
            data[key.strip()] = value.strip()
        return data

    parsed = {}
    qmname = None
    for line in string_table:
        data = get_data_of_line(line[0])
        if "QMNAME" in data:
            qmname = data["QMNAME"]
            parsed[qmname] = data
        elif "INSTANCE" in data:
            instances = parsed[qmname].setdefault("INSTANCES", [])
            instances.append((data["INSTANCE"], data["MODE"]))
    return parsed


agent_section_ibm_mq_managers = AgentSection(
    name="ibm_mq_managers",
    parse_function=parse_ibm_mq_managers,
)


def inventory_ibm_mq_managers(section: Section) -> InventoryResult:
    for item, attrs in section.items():
        yield TableRow(
            path=["software", "applications", "ibm_mq", "managers"],
            key_columns={
                "name": item,
            },
            inventory_columns={
                "instver": attrs["INSTVER"],
                "instname": attrs["INSTNAME"],
                "ha": attrs.get("HA", "n/a"),
            },
            status_columns={
                "standby": attrs["STANDBY"],
                "status": attrs["STATUS"],
            },
        )


inventory_plugin_ibm_mq_managers = InventoryPlugin(
    name="ibm_mq_managers",
    inventory_function=inventory_ibm_mq_managers,
)
