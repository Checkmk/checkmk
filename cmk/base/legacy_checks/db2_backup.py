#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

from cmk.base.check_api import get_age_human_readable, LegacyCheckDefinition
from cmk.base.check_legacy_includes.db2 import parse_db2_dbs
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import IgnoreResultsError

# <<<db2_backup>>>
# [[[db2taddm:CMDBS1]]]
# 2015-03-12-04.00.13.000000

db2_backup_default_levels = (86400 * 14, 86400 * 28)


def inventory_db2_backup(parsed):
    for instance in parsed[1]:
        yield instance, db2_backup_default_levels


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
    if params:
        warn, crit = params
        if age >= crit:
            yield 2, "Time since last backup: %s" % get_age_human_readable(age)
        elif age >= warn:
            yield 1, "Time since last backup: %s" % get_age_human_readable(age)
        else:
            yield 0, "Time since last backup: %s" % get_age_human_readable(age)
    else:
        yield 0, "Time since last backup: %s" % get_age_human_readable(age)


check_info["db2_backup"] = LegacyCheckDefinition(
    parse_function=parse_db2_dbs,
    service_name="DB2 Backup %s",
    check_function=check_db2_backup,
    discovery_function=inventory_db2_backup,
    check_ruleset_name="db2_backup",
)
