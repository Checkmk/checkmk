#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Mapping, Optional, Sequence, Union

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

Instance = Mapping[str, Union[None, str, bool]]

Section = Mapping[str, Instance]

# <<<oracle_instance:sep(124)>>>
# XE|11.2.0.2.0|OPEN|ALLOWED|STOPPED|3524|2752243048|NOARCHIVELOG|PRIMARY|NO|XE|080220151025
# last entry: db creation time 'ddmmyyyyhh24mi'


def create_oracle_instance(info_line: Sequence[str]) -> Instance:
    result: Dict[str, Union[None, str, bool]] = {}
    result['general_error'] = None
    # In case of a general error (e.g. authentication failed), the second
    # column contains the word "FAILURE"
    if info_line[1] == 'FAILURE':
        result['general_error'] = " ".join(info_line[2:])

    # lines can have different length
    line_len = len(info_line)
    result['invalid_data'] = result['general_error'] is not None or line_len not in [6, 11, 12, 22]

    def getcolumn(column_index: int, default: Optional[str] = None) -> Optional[str]:
        if (result['general_error'] and column_index != 0) or column_index >= line_len:
            return default
        return info_line[column_index]

    # assign columns
    result['sid'] = getcolumn(0)
    result['version'] = getcolumn(1)
    result['openmode'] = getcolumn(2)
    result['logins'] = getcolumn(3)
    result['archiver'] = getcolumn(4) if line_len > 6 else None
    result['up_seconds'] = getcolumn(5) if line_len > 6 else None
    # line_len > 6
    result['_dbid'] = getcolumn(6)
    result['log_mode'] = getcolumn(7)
    result['database_role'] = getcolumn(8)
    result['force_logging'] = getcolumn(9)
    result['name'] = getcolumn(10)
    # line_len > 11
    result['db_creation_time'] = getcolumn(11)
    # line_len > 12
    result['pluggable'] = getcolumn(12, "FALSE")
    result['_con_id'] = getcolumn(13)
    result['pname'] = getcolumn(14)
    result['_pdbid'] = getcolumn(15)
    result['popenmode'] = getcolumn(16)
    result['prestricted'] = getcolumn(17)
    result['ptotal_size'] = getcolumn(18)
    result['_precovery_status'] = getcolumn(19)
    result['pup_seconds'] = getcolumn(20)
    result['_pblock_size'] = getcolumn(21)

    result['old_agent'] = False
    result['pdb'] = False

    if not result['general_error']:
        # Detect old oracle agent plugin output
        if line_len == 6:
            result['old_agent'] = True

        # possible multitenant entry?
        # every pdb has a con_id != 0
        if line_len > 12 and result['pluggable'] == 'TRUE' and result['_con_id'] != '0':
            result['pdb'] = True

            if str(result['prestricted']).lower() == 'no':
                result['logins'] = 'RESTRICTED'
            else:
                result['logins'] = 'ALLOWED'

            result['openmode'] = result['popenmode']
            result['up_seconds'] = result['pup_seconds']

    return result


def parse_oracle_instance(string_table: StringTable) -> Section:
    parsed = {}

    for line in string_table:
        if not line:
            continue

        # Skip ORA- error messages from broken old oracle agent
        # <<<oracle_instance:sep(124)>>>
        # ORA-99999 tnsping failed for +ASM1
        if line[0].startswith('ORA-') and line[0][4].isdigit() and len(line[0]) < 16:
            continue

        item_data = create_oracle_instance(line)

        item_name = str(item_data['sid'])

        # Multitenant use DB_NAME.PDB_NAME as Service
        if item_data['pdb']:
            item_name = "%s.%s" % (item_data['sid'], item_data['pname'])

        parsed[item_name] = item_data

    return parsed


register.agent_section(
    name="oracle_instance",
    parse_function=parse_oracle_instance,
)


def _parse_raw_db_creation_time(raw_str) -> Optional[str]:
    """ "%d%m%Y%H%M%S" => "%Y-%m-%d %H:%M"

        >>> _parse_raw_db_creation_time("080220151025")
        '2015-02-08 10:25'

    """

    if not (isinstance(raw_str, str) and raw_str.isdigit() and len(raw_str) == 12):
        return None

    return f"{raw_str[4:8]}-{raw_str[2:4]}-{raw_str[:2]} {raw_str[8:10]}:{raw_str[10:]}"


def inventory_oracle_instance(section: Section) -> InventoryResult:
    path = ["software", "applications", "oracle", "instance"]

    for item_data in sorted(section.values(), key=lambda v: str(v["sid"])):
        if item_data['invalid_data']:
            continue

        try:
            status_columns = {"db_uptime": int(item_data['up_seconds'])}  # type: ignore[arg-type]
        except (TypeError, ValueError):
            status_columns = {}

        yield TableRow(
            path=path,
            key_columns={"sid": item_data['sid']},
            inventory_columns={
                "pname": item_data['pname'],
                "version": item_data['version'],
                "openmode": item_data['openmode'],
                "logmode": item_data['log_mode'],
                "logins": item_data['logins'],
                "db_creation_time": _parse_raw_db_creation_time(item_data['db_creation_time']),
            },
            status_columns=status_columns,
        )


register.inventory_plugin(
    name="oracle_instance",
    inventory_function=inventory_oracle_instance,
)
