#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.check_legacy_includes.db2 import parse_db2_dbs
from cmk.base.config import check_info

from cmk.agent_based.v2 import IgnoreResultsError, render

# <<<db2_backup>>>
# [[[db2taddm:CMDBS1]]]
# 2015-03-12-04.00.13.000000


def inventory_db2_backup(parsed):
    for instance in parsed[1]:
        yield instance, {}


def check_db2_backup(item, params, parsed):
    db = parsed[1].get(item)
    if not db:
        raise IgnoreResultsError("Login into database failed")

    try:
        last_backup = time.mktime(time.strptime(db[0][0][:19], "%Y-%m-%d-%H.%M.%S"))
    except Exception:
        if db[0][0] == "-":
            yield 1, "No backup available"
        else:
            yield 3, "Last backup contains an invalid timestamp: %s" % db[0][0]
        return

    age = time.time() - last_backup
    yield check_levels(
        age,
        None,
        params["levels"],
        human_readable_func=render.timespan,
        infoname="Time since last backup",
    )


check_info["db2_backup"] = LegacyCheckDefinition(
    parse_function=parse_db2_dbs,
    service_name="DB2 Backup %s",
    discovery_function=inventory_db2_backup,
    check_function=check_db2_backup,
    check_ruleset_name="db2_backup",
    check_default_parameters={
        "levels": (86400 * 14, 86400 * 28),
    },
)
