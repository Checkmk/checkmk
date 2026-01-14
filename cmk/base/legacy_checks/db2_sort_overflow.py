#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import IgnoreResultsError
from cmk.plugins.db2.agent_based.lib import parse_db2_dbs

check_info = {}

# <<<db2_sort_overflow>>>
# [[[test:datenbank1]]]
# Total sorts 100
# Sort overflows 3


def discover_db2_sort_overflow(parsed):
    for key in parsed[1]:
        yield key, {}


def check_db2_sort_overflow(item, params, parsed):
    db = parsed[1].get(item)
    if not db:
        raise IgnoreResultsError("Login into database failed")

    total, overflows = tuple(float(x[-1]) for x in db)
    if total > 0:
        overflow_perc = overflows * 100 / total
    else:
        overflow_perc = 0.0
    warn, crit = params.get("levels_perc")
    if overflow_perc >= crit:
        yield 2, f"{overflow_perc:.1f}% sort overflow (levels at {warn:.1f}%/{crit:.1f}%)"
    elif overflow_perc >= warn:
        yield 1, f"{overflow_perc:.1f}% sort overflow (levels at {warn:.1f}%/{crit:.1f}%)"
    else:
        yield 0, "%.1f%% sort overflow" % overflow_perc

    yield 0, "Sort overflows: %d" % overflows
    yield 0, "Total sorts: %d" % total, [("sort_overflow", overflow_perc, warn, crit, 0, 100)]


check_info["db2_sort_overflow"] = LegacyCheckDefinition(
    name="db2_sort_overflow",
    parse_function=parse_db2_dbs,
    service_name="DB2 Sort Overflow %s",
    discovery_function=discover_db2_sort_overflow,
    check_function=check_db2_sort_overflow,
    check_ruleset_name="db2_sortoverflow",
    check_default_parameters={"levels_perc": (2.0, 4.0)},
)
