#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<oracle_recovery_area>>>
# TUX12C 0 4800 19 0

# Columns:
# ORACLE_SID used_pct size used reclaimable


from cmk.base.check_api import get_bytes_human_readable, LegacyCheckDefinition, MKCounterWrapped
from cmk.base.config import check_info, factory_settings

factory_settings["oracle_recovery_area_defaults"] = {
    "levels": (70.0, 90.0),
}


def inventory_oracle_recovery_area(info):
    return [(line[0], {}) for line in info]


def check_oracle_recovery_area(item, params, info):
    for line in info:
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
                    get_bytes_human_readable(used_mb * mb),
                    get_bytes_human_readable(size_mb * mb),
                    perc_used,
                    warn,
                    crit,
                    get_bytes_human_readable(reclaimable_mb * mb),
                ),
                [("used", used_mb, warn_mb, crit_mb, 0, size_mb), ("reclaimable", reclaimable_mb)],
            )

    # In case of missing information we assume that the login into
    # the database has failed and we simply skip this check. It won't
    # switch to UNKNOWN, but will get stale.
    raise MKCounterWrapped("Login into database failed")


check_info["oracle_recovery_area"] = LegacyCheckDefinition(
    check_function=check_oracle_recovery_area,
    discovery_function=inventory_oracle_recovery_area,
    service_name="ORA %s Recovery Area",
    default_levels_variable="oracle_recovery_area_defaults",
    check_ruleset_name="oracle_recovery_area",
)
