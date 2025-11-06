#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# Example output:
# <<<mssql_connections>>>
# MSSQLSERVER master 16
# MSSQLSERVER tempdb 1


from collections.abc import Mapping
from typing import NewType, TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    Service,
    StringTable,
)

MSSQLConnections = NewType("MSSQLConnections", Mapping[str, int])


class CheckParams(TypedDict):
    levels: LevelsT[int]


def parse_mssql_connections(string_table: StringTable) -> MSSQLConnections:
    parsed: dict[str, int] = {}
    for line in string_table:
        try:
            instance, db_name, connection_count = line
            parsed.setdefault(f"{instance} {db_name}", int(connection_count))
        except ValueError:
            pass
    return MSSQLConnections(parsed)


def inventory_mssql_connections(section: MSSQLConnections) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_mssql_connections(
    item: str, params: CheckParams, section: MSSQLConnections
) -> CheckResult:
    if item not in section:
        return None

    yield from check_levels(
        value=section[item],
        metric_name="connections",
        levels_upper=params["levels"],
        render_func=lambda x: str(int(x)),
        label="Connections",
    )


agent_section_mssql_connections = AgentSection(
    name="mssql_connections",
    parse_function=parse_mssql_connections,
)


check_plugin_mssql_connections = CheckPlugin(
    name="mssql_connections",
    service_name="MSSQL Connections %s",
    discovery_function=inventory_mssql_connections,
    check_function=check_mssql_connections,
    check_ruleset_name="mssql_connections",
    check_default_parameters=CheckParams(
        levels=("no_levels", None),
    ),
)
