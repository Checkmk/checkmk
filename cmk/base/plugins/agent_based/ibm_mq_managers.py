#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

from .agent_based_api.v1 import regex, register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

Section = Mapping[str, Mapping[str, Any]]


def parse_ibm_mq_managers(string_table: StringTable) -> Section:
    re_attributes = regex(r"[()]")

    def get_data_of_line(line):
        splits = re_attributes.split(line)
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


register.agent_section(
    name="ibm_mq_managers",
    parse_function=parse_ibm_mq_managers,
)


def inventory_ibm_mq_managers(section: Section) -> InventoryResult:
    path = ["software", "applications", "ibm_mq", "managers"]
    for item, attrs in section.items():
        yield TableRow(
            path=path,
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


register.inventory_plugin(
    name="ibm_mq_managers",
    inventory_function=inventory_ibm_mq_managers,
)
