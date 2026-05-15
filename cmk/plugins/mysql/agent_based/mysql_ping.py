#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.mysql.agent_based.lib import mysql_parse_per_item

# <<<mysql_ping>>>
# [[instance]]
# mysqladmin: connect to server at 'localhost' failed
# error: 'Access denied for user 'root'@'localhost' (using password: NO)'
#


Section = Mapping[str, Sequence[Sequence[str]]]


def _parse_mysql_ping_item(lines: Sequence[Sequence[str]]) -> Sequence[Sequence[str]]:
    return lines


def parse_mysql_ping(string_table: StringTable) -> Section:
    return mysql_parse_per_item(_parse_mysql_ping_item)(string_table)


def check_mysql_ping(item: str, section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    message = " ".join(data[0])
    if message == "mysqld is alive":
        yield Result(state=State.OK, summary="MySQL Daemon is alive")
    else:
        yield Result(state=State.CRIT, summary=message)


def discover_mysql_ping(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


agent_section_mysql_ping = AgentSection(
    name="mysql_ping",
    parse_function=parse_mysql_ping,
)


check_plugin_mysql_ping = CheckPlugin(
    name="mysql_ping",
    service_name="MySQL Instance %s",
    discovery_function=discover_mysql_ping,
    check_function=check_mysql_ping,
)
