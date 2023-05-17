#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import check_levels, get_age_human_readable, LegacyCheckDefinition
from cmk.base.check_legacy_includes.uptime import parse_snmp_uptime
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.ups import DETECT_UPS_GENERIC

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
    "1": 0,
    "2": 1,
    "3": 2,
    "4": 2,
    "5": 0,
    "6": 0,
}


def discover_ups_test(info):
    if info[1]:
        return [(None, {})]
    return None


def check_ups_test(_no_item, params, info):
    uptime_info, bat_info = info
    if not uptime_info or not bat_info:
        return

    results_summary, raw_start_time, ups_test_results_detail = bat_info[0]
    uptime = parse_snmp_uptime(uptime_info[0][0])
    start_time = parse_snmp_uptime(raw_start_time)

    # The MIB dictates a set of possible values for the test result, which are all
    # included in the result mapping.
    # However, the device could still have a test result that is outside the set of
    # possible values (e.g. "0"). In this case, an UNKNOWN state is chosen because
    # it reflects the truth and the check is able to show further check results.
    state = _SUMMARY_STATE_MAP.get(results_summary, 3)
    details = f" ({ups_test_results_detail})" if ups_test_results_detail else ""
    yield state, f"Last test: {_TEST_RESULT_SUMMARY_MAP.get(results_summary, 'unknown')}{details}"

    if start_time:
        label = "Time since start of last test"
    else:
        yield 0, "No battery test since start of device"
        label = "Uptime"

    # Elapsed time since last start of test
    yield check_levels(
        uptime - start_time,
        None,
        params.get("levels_elapsed_time"),
        human_readable_func=get_age_human_readable,
        infoname=label,
    )


check_info["ups_test"] = LegacyCheckDefinition(
    detect=DETECT_UPS_GENERIC,
    discovery_function=discover_ups_test,
    check_function=check_ups_test,
    service_name="Self Test",
    check_ruleset_name="ups_test",
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
    default_levels_variable="ups_test_default_levels",
    check_default_parameters={
        "levels_elapsed_time": None,
    },
)

factory_settings["ups_test_default_levels"] = {
    "levels_elapsed_time": None,
}
