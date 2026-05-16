#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State,
)
from cmk.plugins.db2.agent_based.lib import parse_db2_dbs, Section

# <<<db2_sort_overflow>>>
# [[[test:datenbank1]]]
# Total sorts 100
# Sort overflows 3


def discover_db2_sort_overflow(section: Section) -> DiscoveryResult:
    for key in section[1]:
        yield Service(item=key)


def check_db2_sort_overflow(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    db = section[1].get(item)
    if not db:
        raise IgnoreResultsError("Login into database failed")

    total, overflows = (float(x[-1]) for x in db)
    if total > 0:
        overflow_perc = overflows * 100 / total
    else:
        overflow_perc = 0.0
    warn, crit = params["levels_perc"]
    if overflow_perc >= crit:
        yield Result(
            state=State.CRIT,
            summary=f"{overflow_perc:.1f}% sort overflow (levels at {warn:.1f}%/{crit:.1f}%)",
        )
    elif overflow_perc >= warn:
        yield Result(
            state=State.WARN,
            summary=f"{overflow_perc:.1f}% sort overflow (levels at {warn:.1f}%/{crit:.1f}%)",
        )
    else:
        yield Result(state=State.OK, summary=f"{overflow_perc:.1f}% sort overflow")

    yield Result(state=State.OK, summary=f"Sort overflows: {int(overflows)}")
    yield Result(state=State.OK, summary=f"Total sorts: {int(total)}")
    yield Metric("sort_overflow", overflow_perc, levels=(warn, crit), boundaries=(0, 100))


agent_section_db2_sort_overflow = AgentSection(
    name="db2_sort_overflow",
    parse_function=parse_db2_dbs,
)


check_plugin_db2_sort_overflow = CheckPlugin(
    name="db2_sort_overflow",
    service_name="DB2 Sort Overflow %s",
    discovery_function=discover_db2_sort_overflow,
    check_function=check_db2_sort_overflow,
    check_ruleset_name="db2_sortoverflow",
    check_default_parameters={"levels_perc": (2.0, 4.0)},
)
