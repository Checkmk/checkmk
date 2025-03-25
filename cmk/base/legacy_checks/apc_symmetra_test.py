#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.apc import DETECT

check_info = {}


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


def check_apc_test(item, params, info):
    days_warn, days_crit = params.get("levels_elapsed_time") or (0, 0)  # TODO: clean this up
    if not info:
        return 3, "Data Missing"
    last_result = int(info[0][0])
    last_date = info[0][1]

    try:
        # I don't have any SNMP walk to confirm this, but in some cases
        # last_date has the value 'Unknown' according to the previous source
        # code.
        days_diff = _days_difference(last_date, datetime.date.today())
    except ValueError:
        return 3, "Date of last self test is unknown"

    diagnostic_status_text = {1: "OK", 2: "failed", 3: "invalid", 4: "in progress"}

    state = 0
    diag_label = ""
    if last_result == 2:
        state = 2
        diag_label = "(!!)"
    elif last_result == 3:
        state = 1
        diag_label = "(!)"

    time_label = ""
    if days_crit and days_diff >= days_crit:
        state = 2
        time_label = "(!!)"
    elif days_warn and days_diff >= days_warn:
        state = max(state, 1)
        time_label = "(!)"

    return state, "Result of self test: {}{}, Date of last test: {}{}".format(
        diagnostic_status_text.get(last_result, "-"),
        diag_label,
        last_date,
        time_label,
    )


def inventory_apc_test(info):
    if info:
        return [(None, {})]
    return []


def parse_apc_symmetra_test(string_table: StringTable) -> StringTable:
    return string_table


check_info["apc_symmetra_test"] = LegacyCheckDefinition(
    name="apc_symmetra_test",
    parse_function=parse_apc_symmetra_test,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.1.7.2",
        oids=["3", "4"],
    ),
    service_name="Self Test",
    discovery_function=inventory_apc_test,
    check_function=check_apc_test,
    check_ruleset_name="ups_test",
    check_default_parameters={
        "levels_elapsed_time": None,
    },
)
