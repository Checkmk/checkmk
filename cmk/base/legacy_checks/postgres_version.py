#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<postgres_version>>>
# PostgreSQL 9.3.6 on x86_64-unknown-linux-gnu, compiled by gcc (Ubuntu 4.8.2-19ubuntu1) 4.8.2, 64-bit
#
# # instance
# <<<postgres_version>>>
# [[[foobar]]]
# PostgreSQL 9.3.6 on x86_64-unknown-linux-gnu, compiled by gcc (Ubuntu 4.8.2-19ubuntu1) 4.8.2, 64-bit
#
# # In case the server has been stopped:
# <<<postgres_version:sep(1)>>>
#
# psql: could not connect to server: No such file or directory
#     Is the server running locally and accepting
#     connections on Unix domain socket "/var/run/postgresql/.s.PGSQL.5437"?
#


# mypy: disable-error-code="var-annotated"

from cmk.base.check_api import discover, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import IgnoreResultsError


def parse_postgres_version(info):
    parsed = {}
    instance_name = ""
    for line in info:
        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            instance_name = line[0][3:-3]
            continue
        parsed.setdefault(instance_name, " ".join(line))
    return parsed


def check_postgres_version(item, _no_params, parsed):
    if not (data := parsed.get(item)):
        return
    if "could not connect" in data:
        raise IgnoreResultsError("Login into database failed")
    yield 0, data


check_info["postgres_version"] = LegacyCheckDefinition(
    parse_function=parse_postgres_version,
    discovery_function=discover(),
    check_function=check_postgres_version,
    service_name="PostgreSQL Version %s",
)
