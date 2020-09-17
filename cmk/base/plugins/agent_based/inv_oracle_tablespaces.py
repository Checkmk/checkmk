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
from .utils.oracle import SectionTableSpaces


def inventory_oracle_tablespaces(section: SectionTableSpaces) -> InventoryResult:
    path_tablespaces = ["software", "applications", "oracle", "tablespaces"]
    tablespaces = section["tablespaces"]
    for tablespace in sorted(tablespaces):
        sid, name = tablespace
        attrs = tablespaces[tablespace]
        db_version = attrs["db_version"]
        num_files = 0
        num_avail = 0
        num_extensible = 0
        current_size = 0
        max_size = 0
        used_size = 0
        num_increments = 0

        for datafile in attrs.get("datafiles", []):
            # The following values may be None, see related check plugin
            # free_space and increment_size are already scaled by block_size
            free_space = datafile["free_space"]
            increment_size = datafile["increment_size"]
            if not (isinstance(free_space, int) and isinstance(increment_size, int)):
                continue

            num_files += 1
            if datafile["status"] not in ["AVAILABLE", "ONLINE", "READONLY"
                                         ] or datafile["size"] is None or datafile[
                                             "free_space"] is None or datafile["max_size"] is None:

                continue

            df_size = datafile["size"]
            df_free_space = datafile["free_space"]
            df_max_size = datafile["max_size"]

            num_avail += 1
            current_size += df_size
            used_size += df_size - df_free_space

            # Autoextensible? Honor max size. Everything is computed in
            # *Bytes* here!
            if datafile["autoextensible"] and datafile["increment_size"] is not None:
                num_extensible += 1
                incsize = datafile["increment_size"]

                if df_size > df_max_size:
                    max_size += df_size
                    free_extension = df_size - df_max_size  # free extension space
                else:
                    max_size += df_max_size
                    free_extension = df_max_size - df_size  # free extension space

                #incs, rest = divmod(free_extension, incsize)
                #if rest:
                #    # ??? Was ist, wenn es nicht genau aufgeht und ein weiteres
                #    # increment max_size ueberschreiten würde? Das geht ja wohl
                #    # nicht oder??
                #    # incs += 1 ### Dann wuerde max_size überschritten!
                incs = int(free_extension / incsize)
                num_increments += incs
                increment_size += incsize * incs

                if float(db_version) >= 11:
                    # The size of next extent in datafile is ignored when remaining
                    # free space is > then next extend. Oracle uses all space up to the maximum!
                    free_space += df_max_size - df_size
                else:
                    # The free space in this table is the current free space plus
                    # the additional space that can be gathered by using all available
                    # remaining increments
                    free_space += increment_size + df_free_space

            # not autoextensible: take current size as maximum
            else:
                max_size += df_size
                free_space += df_free_space

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
