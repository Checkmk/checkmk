#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Optional, Tuple, TypedDict
from contextlib import suppress

from .agent_based_api.v0.type_defs import AgentStringTable
from .agent_based_api.v0 import register


class MSSQLInstanceData(TypedDict):
    unlimited: bool
    max_size: Optional[float]
    allocated_size: Optional[float]
    used_size: Optional[float]


SectionDatafiles = Dict[Tuple[Optional[str], str, str], MSSQLInstanceData]


def parse_mssql_datafiles(string_table: AgentStringTable) -> SectionDatafiles:
    section: SectionDatafiles = {}
    for line in string_table:
        if line[-1].startswith("ERROR: "):
            continue
        if len(line) == 6:
            inst = None
            database, file_name, _physical_name, max_size, allocated_size, used_size = line
            unlimited = False
        elif len(line) == 8:
            inst, database, file_name, _physical_name, max_size, allocated_size, used_size = line[:
                                                                                                  7]
            unlimited = line[7] == '1'
        else:
            continue

        mssql_instance = section.setdefault((inst, database, file_name), {
            "unlimited": unlimited,
            "max_size": None,
            "allocated_size": None,
            "used_size": None,
        })
        with suppress(ValueError):
            mssql_instance["max_size"] = float(max_size) * 1024 * 1024
        with suppress(ValueError):
            mssql_instance["allocated_size"] = float(allocated_size) * 1024 * 1024
        with suppress(ValueError):
            mssql_instance["used_size"] = float(used_size) * 1024 * 1024

    return section


register.agent_section(
    name="mssql_datafiles",
    parse_function=parse_mssql_datafiles,
)

register.agent_section(
    name="mssql_transactionlogs",
    parse_function=parse_mssql_datafiles,
)
