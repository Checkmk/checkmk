#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<oracle_longactivesessions:seq(124)>>>
# instance_name | sid | serial | machine | process | osuser | program | last_call_el | sql_id

# Columns:
# ORACLE_SID serial# machine process osuser program last_call_el sql_id


from cmk.base.check_api import get_age_human_readable, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import IgnoreResultsError


def inventory_oracle_longactivesessions(info):
    return [(line[0], {}) for line in info]


def check_oracle_longactivesessions(item, params, info):
    sessioncount = 0
    state = 3
    itemfound = False

    for line in info:
        if len(line) <= 1:
            continue

        warn, crit = params["levels"]

        if line[0] == item:
            itemfound = True

        if line[0] == item and line[1] != "":
            sessioncount += 1
            _sid, sidnr, serial, machine, process, osuser, program, last_call_el, sql_id = line

            longoutput = (
                "Session (sid,serial,proc) %s %s %s active for %s from %s osuser %s program %s sql_id %s "
                % (
                    sidnr,
                    serial,
                    process,
                    get_age_human_readable(int(last_call_el)),
                    machine,
                    osuser,
                    program,
                    sql_id,
                )
            )

    if itemfound:
        infotext = "%s" % sessioncount
        perfdata = [("count", sessioncount, warn, crit)]
        if sessioncount == 0:
            return 0, infotext, perfdata

        if sessioncount >= crit:
            state = 2
        elif sessioncount >= warn:
            state = 1
        else:
            state = 0

        if state:
            infotext += " (warn/crit at %d/%d)" % (warn, crit)

        if sessioncount <= 10:
            infotext += " %s" % longoutput

        return state, infotext, perfdata

    # In case of missing information we assume that the login into
    # the database has failed and we simply skip this check. It won't
    # switch to UNKNOWN, but will get stale.
    raise IgnoreResultsError("no info from database. Check ORA %s Instance" % item)


check_info["oracle_longactivesessions"] = LegacyCheckDefinition(
    service_name="ORA %s Long Active Sessions",
    discovery_function=inventory_oracle_longactivesessions,
    check_function=check_oracle_longactivesessions,
    check_ruleset_name="oracle_longactivesessions",
    check_default_parameters={
        "levels": (500, 1000),
    },
)
