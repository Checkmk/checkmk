#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output:
# <<<mssql_connections>>>
# MSSQLSERVER master 16
# MSSQLSERVER tempdb 1


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition

check_info = {}


def parse_mssql_connections(string_table):
    parsed = {}
    for line in string_table:
        try:
            instance, db_name, connection_count = line
            connection_count = int(connection_count)
            parsed.setdefault(f"{instance} {db_name}", connection_count)
        except ValueError:
            pass
    return parsed


def inventory_mssql_connections(parsed):
    for item in parsed:
        yield item, {}


def check_mssql_connections(item, params, parsed):
    # If a database is missing in the agent output there are no
    # active connections for that database.
    return check_levels(
        parsed.get(item, 0),
        "connections",
        params["levels"],
        human_readable_func=int,
        infoname="Connections",
    )


check_info["mssql_connections"] = LegacyCheckDefinition(
    name="mssql_connections",
    parse_function=parse_mssql_connections,
    service_name="MSSQL Connections %s",
    discovery_function=inventory_mssql_connections,
    check_function=check_mssql_connections,
    check_ruleset_name="mssql_connections",
    check_default_parameters={
        "levels": None,
    },
)
