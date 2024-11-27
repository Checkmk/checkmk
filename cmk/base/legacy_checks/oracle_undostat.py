#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# In cooperation with Thorsten Bruhns from OPITZ Consulting

# <<<oracle_undostat>>>
# TUX2 160 0 1081 300 0


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import IgnoreResultsError, render

check_info = {}


def parse_oracle_undostat(string_table):
    return {line[0]: [int(v) for v in line[1:]] for line in string_table if len(line) == 6}


def discover_oracle_undostat(parsed):
    for item in parsed:
        yield item, {}


def check_oracle_undostat(item, params, parsed):
    data = parsed.get(item)
    if data is None:
        # In case of missing information we assume that the login into
        # the database has failed and we simply skip this check. It won't
        # switch to UNKNOWN, but will get stale.
        raise IgnoreResultsError("Login into database failed")

    activeblks, maxconcurrency, tuned_undoretention, maxquerylen, nospaceerrcnt = data
    warn, crit = params["levels"]

    yield check_levels(
        tuned_undoretention,
        None,
        params=None if tuned_undoretention == -1 else (None, None, warn, crit),
        human_readable_func=str if tuned_undoretention == -1 else render.timespan,
        infoname="Undo retention",
    )

    if tuned_undoretention >= 0:
        yield 0, "Active undo blocks: %d" % activeblks

    yield 0, "Max concurrent transactions: %d" % maxconcurrency
    yield 0, "Max querylen: %s" % render.timespan(maxquerylen)
    state_errcnt = params["nospaceerrcnt_state"] if nospaceerrcnt else 0
    yield state_errcnt, "Space errors: %d" % nospaceerrcnt

    yield (
        0,
        "",
        [
            ("activeblk", activeblks),
            ("transconcurrent", maxconcurrency),
            # lower levels are unorthodox here (at least), but we keep it for compatibility (for now)
            ("tunedretention", tuned_undoretention, warn, crit),
            ("querylen", maxquerylen),
            ("nonspaceerrcount", nospaceerrcnt),
        ],
    )


check_info["oracle_undostat"] = LegacyCheckDefinition(
    name="oracle_undostat",
    parse_function=parse_oracle_undostat,
    service_name="ORA %s Undo Retention",
    discovery_function=discover_oracle_undostat,
    check_function=check_oracle_undostat,
    check_ruleset_name="oracle_undostat",
    check_default_parameters={
        "levels": (600, 300),
        "nospaceerrcnt_state": 2,
    },
)
