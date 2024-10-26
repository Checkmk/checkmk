#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<oracle_sessions>>>
# pengt  15
# hirni  22
# newdb  47 772 65


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import IgnoreResultsError

check_info = {}


def parse_oracle_sessions(string_table):
    header = ["cursess", "maxsess", "curmax"]
    parsed = {}
    for line in string_table:
        for key, entry in zip(header, line[1:]):
            try:
                parsed.setdefault(line[0], {})[key] = int(entry)
            except ValueError:
                pass
    return parsed


def inventory_oracle_sessions(parsed):
    for sid in parsed:
        yield sid, {}


def check_oracle_sessions(item, params, parsed):
    if isinstance(params, tuple):
        params = {"sessions_abs": params}

    if item in parsed and "cursess" in parsed[item]:
        data = parsed[item]
        sessions = data["cursess"]
        sessions_max = data.get("maxsess")

        if sessions_max is not None:
            state = 0
            infotext = "%d of %d sessions" % (sessions, sessions_max)
            sessions_perc = 100.0 * sessions / sessions_max
            infotext_perc = "%.2f%%" % sessions_perc
            if "sessions_perc" in params:
                warn_perc, crit_perc = params["sessions_perc"]
                if sessions_perc >= crit_perc:
                    state = 2
                elif sessions_perc >= warn_perc:
                    state = 1
                if state:
                    infotext_perc += f" (warn/crit at {warn_perc:.1f}%/{crit_perc:.1f}%)"
            yield state, infotext_perc

        else:
            infotext = "%d sessions" % sessions

        state = 0
        warn, crit = None, None
        if "sessions_abs" in params and params["sessions_abs"] is not None:
            warn, crit = params["sessions_abs"]
            if sessions >= crit:
                state = 2
            elif sessions >= warn:
                state = 1
            if state:
                infotext += " (warn/crit at %d/%d)" % (warn, crit)
        yield state, infotext, [("sessions", sessions, warn, crit, 0, sessions_max)]

        return

    # In case of missing information we assume that the login into
    # the database has failed and we simply skip this check. It won't
    # switch to UNKNOWN, but will get stale.
    raise IgnoreResultsError("Login into database failed")


check_info["oracle_sessions"] = LegacyCheckDefinition(
    name="oracle_sessions",
    parse_function=parse_oracle_sessions,
    service_name="ORA %s Sessions",
    discovery_function=inventory_oracle_sessions,
    check_function=check_oracle_sessions,
    check_ruleset_name="oracle_sessions",
    check_default_parameters={
        "sessions_abs": (150, 300),
    },
)
