#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import InventoryPlugin, InventoryResult, TableRow
from cmk.plugins.lib.oracle_instance import GeneralError, InvalidData, Section


def _parse_raw_db_creation_time(raw_str: str | None) -> str | None:
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
            continue

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
            status_columns={
                "db_uptime": item_data.up_seconds,
                "host": item_data.host_name,
            },
        )


inventory_plugin_oracle_instance = InventoryPlugin(
    name="oracle_instance",
    inventory_function=inventory_oracle_instance,
)
