#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<oracle_recovery_area>>>
# TUX12C 0 4800 19 0

# Columns:
# ORACLE_SID used_pct size used reclaimable


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)


def inventory_oracle_recovery_area(section: StringTable) -> DiscoveryResult:
    yield from (Service(item=line[0]) for line in section)


def check_oracle_recovery_area(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    for line in section:
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
                state = State.CRIT
            elif perc_used >= warn:
                state = State.WARN
            else:
                state = State.OK

            mb = 1024 * 1024
            yield Result(
                state=state,
                summary="%s out of %s used (%.1f%%, warn/crit at %s%%/%s%%), %s reclaimable"
                % (
                    render.bytes(used_mb * mb),
                    render.bytes(size_mb * mb),
                    perc_used,
                    warn,
                    crit,
                    render.bytes(reclaimable_mb * mb),
                ),
            )
            yield Metric("used", used_mb, levels=(warn_mb, crit_mb), boundaries=(0, size_mb))
            yield Metric("reclaimable", reclaimable_mb)
            return

    # In case of missing information we assume that the login into
    # the database has failed and we simply skip this check. It won't
    # switch to UNKNOWN, but will get stale.
    raise IgnoreResultsError("Login into database failed")


def parse_oracle_recovery_area(string_table: StringTable) -> StringTable:
    return string_table


agent_section_oracle_recovery_area = AgentSection(
    name="oracle_recovery_area",
    parse_function=parse_oracle_recovery_area,
)


check_plugin_oracle_recovery_area = CheckPlugin(
    name="oracle_recovery_area",
    service_name="ORA %s Recovery Area",
    discovery_function=inventory_oracle_recovery_area,
    check_function=check_oracle_recovery_area,
    check_ruleset_name="oracle_recovery_area",
    check_default_parameters={
        "levels": (70.0, 90.0),
    },
)
