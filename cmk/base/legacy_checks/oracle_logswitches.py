#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.oracle import (
    oracle_handle_ora_errors,
    oracle_handle_ora_errors_discovery,
)

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import IgnoreResultsError, StringTable

check_info = {}

# <<<oracle_logswitches>>>
# pengt  15
# hirni  22


def inventory_oracle_logswitches(info):
    oracle_handle_ora_errors_discovery(info)
    return [(line[0], {}) for line in info if len(line) == 2]


def check_oracle_logswitches(item, params, info):
    if isinstance(params, tuple):
        params = {
            "levels": (params[2], params[3]),
            "levels_lower": (params[0], params[1]),
        }

    for line in info:
        if line[0] == item:
            err = oracle_handle_ora_errors(line)
            if err is False:
                continue
            if isinstance(err, tuple):
                return err
            if len(line) != 2:
                continue

            lowarn, locrit = params["levels_lower"]
            warn, crit = params["levels"]
            logswitches = int(line[1])
            infotext = (
                "%d log switches in the last 60 minutes (warn/crit below %d/%d) (warn/crit at %d/%d)"
                % (logswitches, locrit, lowarn, warn, crit)
            )
            perfdata = [("logswitches", logswitches, warn, crit, 0, None)]
            if logswitches >= crit or logswitches <= locrit:
                return (2, infotext, perfdata)
            if logswitches >= warn or logswitches <= lowarn:
                return (1, infotext, perfdata)
            return (0, infotext, perfdata)

    # In case of missing information we assume that the login into
    # the database has failed and we simply skip this check. It won't
    # switch to UNKNOWN, but will get stale.
    raise IgnoreResultsError("Login into database failed")


def parse_oracle_logswitches(string_table: StringTable) -> StringTable:
    return string_table


check_info["oracle_logswitches"] = LegacyCheckDefinition(
    name="oracle_logswitches",
    parse_function=parse_oracle_logswitches,
    service_name="ORA %s Logswitches",
    discovery_function=inventory_oracle_logswitches,
    check_function=check_oracle_logswitches,
    check_ruleset_name="oracle_logswitches",
    check_default_parameters={
        "levels": (50, 100),
        "levels_lower": (-1, -1),
    },
)
