#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from typing import Mapping, Optional, Sequence, Union

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

# <<<oracle_instance:sep(124)>>>
# XE|11.2.0.2.0|OPEN|ALLOWED|STOPPED|3524|2752243048|NOARCHIVELOG|PRIMARY|NO|XE|080220151025
# last entry: db creation time 'ddmmyyyyhh24mi'


@dataclasses.dataclass(frozen=True)
class InvalidData:
    sid: str


@dataclasses.dataclass(frozen=True)
class GeneralError:
    sid: str
    err: str


@dataclasses.dataclass
class Instance:
    sid: str
    version: Optional[str] = None
    openmode: Optional[str] = None
    logins: Optional[str] = None
    archiver: Optional[str] = None
    up_seconds: Optional[str] = None
    log_mode: Optional[str] = None
    database_role: Optional[str] = None
    force_logging: Optional[str] = None
    name: Optional[str] = None
    db_creation_time: Optional[str] = None
    pluggable: Optional[str] = None
    pname: Optional[str] = None
    popenmode: Optional[str] = None
    prestricted: Optional[str] = None
    ptotal_size: Optional[str] = None
    pup_seconds: Optional[str] = None
    old_agent: bool = False
    pdb: bool = False


Section = Mapping[str, Union[InvalidData, GeneralError, Instance]]


def _parse_agent_line(line: Sequence[str]) -> Union[InvalidData, GeneralError, Instance]:
    sid = line[0]

    # In case of a general error (e.g. authentication failed), the second
    # column contains the word "FAILURE"
    if general_error := " ".join(line[2:]) if line[1] == "FAILURE" else None:
        return GeneralError(
            sid=sid,
            err=general_error,
        )

    # lines can have different length
    if (line_len := len(line)) not in [6, 11, 12, 22]:
        return InvalidData(sid=sid)

    def getcolumn(column_index: int, default: Optional[str] = None) -> Optional[str]:
        return default if column_index >= line_len else line[column_index]

    # assign columns
    instance = Instance(sid)
    instance.version = getcolumn(1)
    instance.openmode = getcolumn(2)
    instance.logins = getcolumn(3)
    instance.archiver = getcolumn(4) if line_len > 6 else None
    instance.up_seconds = getcolumn(5) if line_len > 6 else None
    # line_len > 6
    # 6: dbid
    instance.log_mode = getcolumn(7)
    instance.database_role = getcolumn(8)
    instance.force_logging = getcolumn(9)
    instance.name = getcolumn(10)
    # line_len > 11
    instance.db_creation_time = getcolumn(11)
    # line_len > 12
    instance.pluggable = getcolumn(12, "FALSE")
    con_id = getcolumn(13)
    instance.pname = getcolumn(14)
    # 15: pdbid
    instance.popenmode = getcolumn(16)
    instance.prestricted = getcolumn(17)
    instance.ptotal_size = getcolumn(18)
    # 19: precovery_status
    instance.pup_seconds = getcolumn(20)
    # 21: pblock_size

    # Detect old oracle agent plugin output
    instance.old_agent = line_len == 6

    # possible multitenant entry?
    # every pdb has a con_id != 0
    if line_len > 12 and instance.pluggable == "TRUE" and con_id != "0":
        instance.pdb = True

        if str(instance.prestricted).lower() == "no":
            instance.logins = "RESTRICTED"
        else:
            instance.logins = "ALLOWED"

        instance.openmode = instance.popenmode
        instance.up_seconds = instance.pup_seconds

    return instance


def parse_oracle_instance(string_table: StringTable) -> Section:
    parsed = {}

    for line in string_table:
        if not line:
            continue

        # Skip ORA- error messages from broken old oracle agent
        # <<<oracle_instance:sep(124)>>>
        # ORA-99999 tnsping failed for +ASM1
        if line[0].startswith("ORA-") and line[0][4].isdigit() and len(line[0]) < 16:
            continue

        item_data = _parse_agent_line(line)

        item_name = item_data.sid

        # Multitenant use DB_NAME.PDB_NAME as Service
        if (
            isinstance(
                item_data,
                Instance,
            )
            and item_data.pdb
        ):
            item_name = "%s.%s" % (item_data.sid, item_data.pname)

        parsed[item_name] = item_data

    return parsed


register.agent_section(
    name="oracle_instance",
    parse_function=parse_oracle_instance,
)


def _parse_raw_db_creation_time(raw_str: Optional[str]) -> Optional[str]:
    """ "%d%m%Y%H%M%S" => "%Y-%m-%d %H:%M"

    >>> _parse_raw_db_creation_time("080220151025")
    '2015-02-08 10:25'

    """

    if not (isinstance(raw_str, str) and raw_str.isdigit() and len(raw_str) == 12):
        return None

    return f"{raw_str[4:8]}-{raw_str[2:4]}-{raw_str[:2]} {raw_str[8:10]}:{raw_str[10:]}"


def inventory_oracle_instance(section: Section) -> InventoryResult:
    path = ["software", "applications", "oracle", "instance"]

    for item_data in section.values():
        if isinstance(
            item_data,
            InvalidData,
        ):
            continue

        if isinstance(
            item_data,
            GeneralError,
        ):
            yield TableRow(
                path=path,
                key_columns={"sid": item_data.sid},
                inventory_columns={
                    "pname": None,
                    "version": None,
                    "openmode": None,
                    "logmode": None,
                    "logins": None,
                    "db_creation_time": None,
                },
            )
            return

        try:
            status_columns = {"db_uptime": int(item_data.up_seconds)}  # type: ignore[arg-type]
        except (TypeError, ValueError):
            status_columns = {}

        yield TableRow(
            path=path,
            key_columns={"sid": item_data.sid},
            inventory_columns={
                "pname": item_data.pname,
                "version": item_data.version,
                "openmode": item_data.openmode,
                "logmode": item_data.log_mode,
                "logins": item_data.logins,
                "db_creation_time": _parse_raw_db_creation_time(item_data.db_creation_time),
            },
            status_columns=status_columns,
        )


register.inventory_plugin(
    name="oracle_instance",
    inventory_function=inventory_oracle_instance,
)
