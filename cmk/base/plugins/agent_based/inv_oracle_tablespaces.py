#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# AIMSTGD1|/u01/oradata/aimstgd1/temp0104.dbf|TEMP01|ONLINE|YES|90112|3276800|90048|8192|TEMP|32768|ONLINE|0|TEMPORARY
# AIMSTGD1|/u01/oradata/aimstgd1/temp0105.dbf|TEMP01|ONLINE|YES|90112|3276800|90048|8192|TEMP|32768|ONLINE|0|TEMPORARY
# AIMSTGD1|/u01/oradata/aimstgd1/temp0106.dbf|TEMP01|ONLINE|YES|90112|3276800|90048|8192|TEMP|32768|ONLINE|4544|TEMPORARY
# AIMCONS1|/u01/oradata/aimcons1/temp01.dbf|TEMP|ONLINE|YES|262144|2621440|262016|32768|TEMP|8192|ONLINE|258560|TEMPORARY
# AIMCONS1|/u01/oradata/aimcons1/temp02.dbf|TEMP|ONLINE|YES|262144|2621440|262016|32768|TEMP|8192|ONLINE|258688|TEMPORARY

# Order of columns (it is a table of data files, so table spaces appear multiple times)
# 0  database SID
# 1  data file name
# 2  table space name
# 3  status of the data file
# 4  whether the file is auto extensible
# 5  current size of data file in blocks
# 6  maximum size of data file in blocks (if auto extensible)
# 7  currently number of blocks used by user data
# 8  size of next increment in blocks (if auto extensible)
# 9  wheter the file is in use (online)
# 10 block size in bytes
# 11 status of the table space
# 12 free space in the datafile
# 13 Tablespace-Type (PERMANENT, UNDO, TEMPORARY)

from .agent_based_api.v1.type_defs import InventoryResult
from .agent_based_api.v1 import register, TableRow
from .utils.oracle import SectionTableSpaces, analyze_datafiles


def inventory_oracle_tablespaces(section: SectionTableSpaces) -> InventoryResult:
    path_tablespaces = ["software", "applications", "oracle", "tablespaces"]
    tablespaces = section["tablespaces"]
    for tablespace in sorted(tablespaces):
        sid, name = tablespace
        attrs = tablespaces[tablespace]
        db_version = attrs["db_version"]

        (
            current_size,
            used_size,
            max_size,
            free_space,
            num_increments,
            increment_size,
            _,
            _,
            _,
            _,
            _,
        ) = analyze_datafiles(
            attrs["datafiles"],
            db_version,
            sid,
        )
        yield TableRow(
            path=path_tablespaces,
            key_columns={
                "sid": sid,
                "name": name,
            },
            inventory_columns={
                "version": db_version or "",
                "type": attrs["type"],
                "autoextensible": attrs["autoextensible"] and "YES" or "NO",
            },
            status_columns={
                "current_size": current_size,
                "max_size": max_size,
                "used_size": used_size,
                "num_increments": num_increments,
                "increment_size": increment_size,
                "free_space": free_space,
            },
        )


register.inventory_plugin(
    name='inventory_oracle_tablespaces',
    inventory_function=inventory_oracle_tablespaces,
    sections=["oracle_tablespaces"],
)
