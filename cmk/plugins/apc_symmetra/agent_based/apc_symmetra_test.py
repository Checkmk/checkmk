#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# We use the following OIDs:

# PowerNet-MIB::upsAdvTestDiagnosticsResults   .1.3.6.1.4.1.318.1.1.1.7.2.3
# upsAdvTestDiagnosticsResults OBJECT-TYPE
#         SYNTAX INTEGER {
#                 ok(1),
#                 failed(2),
#                 invalidTest(3),
#                 testInProgress(4)
#         }
#         ACCESS read-only
#         STATUS mandatory
#         DESCRIPTION
#                 "The results of the last UPS diagnostics test performed."
#         ::= { upsAdvTest 3 }

# PowerNet-MIB::upsAdvTestLastDiagnosticsDate  .1.3.6.1.4.1.318.1.1.1.7.2.4
# upsAdvTestLastDiagnosticsDate OBJECT-TYPE
#         SYNTAX DisplayString
#         ACCESS read-only
#         STATUS mandatory
#         DESCRIPTION
#                 "The date the last UPS diagnostics test was performed in
#                  mm/dd/yy format."
#         ::= { upsAdvTest 4 }
#


import datetime
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.apc import DETECT


def _days_difference(date: str, today: datetime.date) -> int:
    """Counts the number of days date happend after today.

    >>> today = datetime.date(2020, month = 1, day = 1)
    >>> _days_difference("01/01/20", today)
    0
    >>> _days_difference("1/1/20", today)
    0
    >>> _days_difference("12/31/2019", today)
    1
    >>> _days_difference("01/01/2021", today)
    -366
    """
    month, day, year = (int(i) for i in date.split("/"))
    if year < 100:
        year += 2000
    return (today - datetime.date(year, month, day)).days


# TODO: check this for common code with ups_test


def check_apc_test(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    if not section:
        yield Result(state=State.UNKNOWN, summary="Data Missing")
        return

    last_result = int(section[0][0])
    last_date = section[0][1]

    try:
        # I don't have any SNMP walk to confirm this, but in some cases
        # last_date has the value 'Unknown' according to the previous source
        # code.
        days_diff = _days_difference(last_date, datetime.date.today())
    except ValueError:
        yield Result(state=State.UNKNOWN, summary="Date of last self test is unknown")
        return

    diagnostic_status_text = {1: "OK", 2: "failed", 3: "invalid", 4: "in progress"}

    test_state = State.OK
    if last_result == State.CRIT.value:
        test_state = State.CRIT
    elif last_result == State.UNKNOWN.value:
        test_state = State.WARN

    yield Result(
        state=test_state,
        summary="Result of self test: {}".format(diagnostic_status_text.get(last_result, "-")),
    )

    state = State.OK
    match params:
        case {"levels_elapsed_time": ("fixed", (warn, crit))}:
            if days_diff >= crit:
                state = State.CRIT
            elif days_diff >= warn:
                state = State.WARN

    yield Result(
        state=state,
        summary=f"Date of last test: {last_date}",
    )


def discover_apc_test(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def parse_apc_symmetra_test(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_apc_symmetra_test = SimpleSNMPSection(
    name="apc_symmetra_test",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.1.7.2",
        oids=["3", "4"],
    ),
    parse_function=parse_apc_symmetra_test,
)

check_plugin_apc_symmetra_test = CheckPlugin(
    name="apc_symmetra_test",
    service_name="Self Test",
    discovery_function=discover_apc_test,
    check_function=check_apc_test,
    check_ruleset_name="ups_test",
    check_default_parameters={
        "levels_elapsed_time": ("no_levels", None),
    },
)
