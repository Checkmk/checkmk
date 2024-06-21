#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.mysql import mysql_parse_per_item
from cmk.base.config import check_info

from cmk.agent_based.v2 import StringTable

# <<<mysql_ping>>>
# [[instance]]
# mysqladmin: connect to server at 'localhost' failed
# error: 'Access denied for user 'root'@'localhost' (using password: NO)'
#


def _parse_mysql_ping_item(lines: Sequence[Sequence[str]]) -> Sequence[Sequence[str]]:
    return lines


def parse_mysql_ping(string_table: StringTable) -> Mapping[str, Any]:
    return mysql_parse_per_item(_parse_mysql_ping_item)(string_table)


def check_mysql_ping(item, _no_params, parsed):
    if not (data := parsed.get(item)):
        return
    message = " ".join(data[0])
    if message == "mysqld is alive":
        yield 0, "MySQL Daemon is alive"
    else:
        yield 2, message


def discover_mysql_ping(section):
    yield from ((item, {}) for item in section)


check_info["mysql_ping"] = LegacyCheckDefinition(
    parse_function=parse_mysql_ping,
    service_name="MySQL Instance %s",
    discovery_function=discover_mysql_ping,
    check_function=check_mysql_ping,
)
