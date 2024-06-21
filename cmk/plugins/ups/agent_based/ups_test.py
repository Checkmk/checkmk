#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.ups import DETECT_UPS_GENERIC
from cmk.plugins.lib.uptime import parse_snmp_uptime

# Description of OIDs used from RFC 1628
# OID: 1.3.6.1.2.1.33.1.7.3
# upsTestResultsSummary OBJECT-TYPE
# SYNTAX INTEGER {
#     donePass(1),
#     doneWarning(2),
#     doneError(3),
#     aborted(4),
#     inProgress(5),
#     noTestsInitiated(6)
# }
# MAX-ACCESS read-only
# STATUS current
# DESCRIPTION
# "The results of the current or last UPS diagnostics
# test performed. The values for donePass(1),
# doneWarning(2), and doneError(3) indicate that the
# test completed either successfully, with a warning, or
# with an error, respectively. The value aborted(4) is
# returned for tests which are aborted by setting the
# value of upsTestId to upsTestAbortTestInProgress.
# Tests which have not yet concluded are indicated by
# inProgress(5). The value noTestsInitiated(6)
# indicates that no previous test results are available,
# such as is the case when no tests have been run since
# the last reinitialization of the network management
# subsystem and the system has no provision for non-
# volatile storage of test results."

# OID: 1.3.6.1.2.1.33.1.7.4
# upsTestResultsDetail OBJECT-TYPE
# SYNTAX DisplayString (SIZE (0..255))
# MAX-ACCESS read-only
# STATUS current
# DESCRIPTION
# "Additional information about upsTestResultsSummary.
# If no additional information available, a zero length
# string is returned."

# OID: 1.3.6.1.2.1.33.1.7.5
# Description:
# upsTestStartTime OBJECT-TYPE
# SYNTAX TimeStamp
# MAX-ACCESS read-only
# STATUS current
# DESCRIPTION
# "The value of sysUpTime at the time the test in
# progress was initiated, or, if no test is in progress,
# the time the previous test was initiated. If the
# value of upsTestResultsSummary is noTestsInitiated(6),
# upsTestStartTime has the value 0."


_TEST_RESULT_SUMMARY_MAP = {
    "1": "passed",
    "2": "warning",
    "3": "error",
    "4": "aborted",
    "5": "in progress",
    "6": "no tests initiated",
}

_SUMMARY_STATE_MAP = {
    "1": State.OK,
    "2": State.WARN,
    "3": State.CRIT,
    "4": State.CRIT,
    "5": State.OK,
    "6": State.OK,
}


def discover_ups_test(section: Sequence[StringTable]) -> DiscoveryResult:
    if section[1]:
        yield Service()


def check_ups_test(params: Mapping[str, Any], section: Sequence[StringTable]) -> CheckResult:
    uptime_info, bat_info = section
    if not uptime_info or not bat_info:
        return

    results_summary, raw_start_time, ups_test_results_detail = bat_info[0]
    uptime = parse_snmp_uptime([[uptime_info[0][0], ""]])
    start_time = parse_snmp_uptime([[raw_start_time, ""]])

    # The MIB dictates a set of possible values for the test result, which are all
    # included in the result mapping.
    # However, the device could still have a test result that is outside the set of
    # possible values (e.g. "0"). In this case, an UNKNOWN state is chosen because
    # it reflects the truth and the check is able to show further check results.
    state = _SUMMARY_STATE_MAP.get(results_summary, State.UNKNOWN)
    details = f" ({ups_test_results_detail})" if ups_test_results_detail else ""
    yield Result(
        state=state,
        summary=f"Last test: {_TEST_RESULT_SUMMARY_MAP.get(results_summary, 'unknown')}{details}",
    )

    if (
        start_time is None
        or uptime is None
        or start_time.uptime_sec is None
        or uptime.uptime_sec is None
    ):
        yield Result(
            state=State.UNKNOWN, summary="Could not determine time since start of last test"
        )
        return

    if start_time.uptime_sec == 0:
        yield Result(state=State.OK, summary="No battery test since start of device")
        label = "Uptime"
        elapsed_time = uptime.uptime_sec

    elif (elapsed_time := uptime.uptime_sec - start_time.uptime_sec) < 0:
        yield Result(
            state=State.UNKNOWN, summary="Could not determine time since start of last test"
        )
        return
    else:
        label = "Time since start of last test"

    # Elapsed time since last start of test
    yield from check_levels(
        elapsed_time,
        metric_name=None,
        levels_upper=params.get("levels_elapsed_time"),
        render_func=render.timespan,
        label=label,
    )


def parse_ups_test(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


snmp_section_ups_test = SNMPSection(
    name="ups_test",
    detect=DETECT_UPS_GENERIC,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.1.3",
            oids=["0"],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.33.1.7",
            oids=["3", "5", "4"],
        ),
    ],
    parse_function=parse_ups_test,
)
check_plugin_ups_test = CheckPlugin(
    name="ups_test",
    service_name="Self Test",
    discovery_function=discover_ups_test,
    check_function=check_ups_test,
    check_ruleset_name="ups_test",
    check_default_parameters={
        "levels_elapsed_time": None,
    },
)
