#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<oracle_recovery_area>>>
# TUX12C 0 4800 19 0

# Columns:
# ORACLE_SID used_pct size used reclaimable


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import IgnoreResultsError, render, StringTable

check_info = {}


def inventory_oracle_recovery_area(info):
    return [(line[0], {}) for line in info]


def check_oracle_recovery_area(item, params, info):
    for line in info:
        if len(line) < 5:
            continue
        if line[0] == item:
            size_mb, used_mb, reclaimable_mb = map(int, line[2:5])
            if size_mb == 0:
                perc_used = 0.0
            else:
                perc_used = float(used_mb - reclaimable_mb) / size_mb * 100

            warn, crit = params["levels"]
            warn_mb = size_mb * warn / 100
            crit_mb = size_mb * crit / 100

            if perc_used >= crit:
                state = 2
            elif perc_used >= warn:
                state = 1
            else:
                state = 0

            mb = 1024 * 1024
            return (
                state,
                "%s out of %s used (%.1f%%, warn/crit at %s%%/%s%%), %s reclaimable"
                % (
                    render.bytes(used_mb * mb),
                    render.bytes(size_mb * mb),
                    perc_used,
                    warn,
                    crit,
                    render.bytes(reclaimable_mb * mb),
                ),
                [("used", used_mb, warn_mb, crit_mb, 0, size_mb), ("reclaimable", reclaimable_mb)],
            )

    # In case of missing information we assume that the login into
    # the database has failed and we simply skip this check. It won't
    # switch to UNKNOWN, but will get stale.
    raise IgnoreResultsError("Login into database failed")


def parse_oracle_recovery_area(string_table: StringTable) -> StringTable:
    return string_table


check_info["oracle_recovery_area"] = LegacyCheckDefinition(
    name="oracle_recovery_area",
    parse_function=parse_oracle_recovery_area,
    service_name="ORA %s Recovery Area",
    discovery_function=inventory_oracle_recovery_area,
    check_function=check_oracle_recovery_area,
    check_ruleset_name="oracle_recovery_area",
    check_default_parameters={
        "levels": (70.0, 90.0),
    },
)
