#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# <<<postgres_conn_time>>>
# 0.063

# instances
# <<<postgres_conn_time>>>
# [[[foobar]]]
# 0.063


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import IgnoreResultsError

check_info = {}


def parse_postgres_conn_time(string_table):
    parsed = {}
    instance_name = ""
    for line in string_table:
        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            instance_name = line[0][3:-3].upper()
            continue
        parsed.setdefault(instance_name, float(line[0]))
    return parsed


def discover_postgres_conn_time(parsed):
    for instance_name in parsed:
        yield instance_name, None


def check_postgres_conn_time(item, _no_params, parsed):
    if item in parsed:
        conn_time = parsed[item]
        return 0, "%s seconds" % conn_time, [("connection_time", conn_time)]

    # In case of missing information we assume that the login into
    # the database has failed and we simply skip this check. It won't
    # switch to UNKNOWN, but will get stale.
    raise IgnoreResultsError("Login into database failed")


check_info["postgres_conn_time"] = LegacyCheckDefinition(
    name="postgres_conn_time",
    parse_function=parse_postgres_conn_time,
    service_name="PostgreSQL Connection Time %s",
    discovery_function=discover_postgres_conn_time,
    check_function=check_postgres_conn_time,
)
