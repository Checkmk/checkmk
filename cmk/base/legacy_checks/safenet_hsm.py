#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="list-item"

import time

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import any_of, get_rate, get_value_store, SNMPTree, startswith

check_info = {}


def parse_safenet_hsm(string_table):
    return (
        {
            "operation_requests": int(string_table[0][0]),
            "operation_errors": int(string_table[0][1]),
            "critical_events": int(string_table[0][2]),
            "noncritical_events": int(string_table[0][3]),
        }
        if string_table
        else None
    )


# .
#   .--Event stats---------------------------------------------------------.
#   |          _____                 _         _        _                  |
#   |         | ____|_   _____ _ __ | |_   ___| |_ __ _| |_ ___            |
#   |         |  _| \ \ / / _ \ '_ \| __| / __| __/ _` | __/ __|           |
#   |         | |___ \ V /  __/ | | | |_  \__ \ || (_| | |_\__ \           |
#   |         |_____| \_/ \___|_| |_|\__| |___/\__\__,_|\__|___/           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_safenet_hsm_events(parsed):
    if parsed:
        return [(None, {})]
    return []


def check_safenet_hsm_events(_no_item, params, parsed):
    now = time.time()

    def check_events(event_type):
        events = parsed[event_type + "_events"]
        infotext = "%d %s events since last reset" % (events, event_type)
        if params.get(event_type + "_events"):
            warn, crit = params[event_type + "_events"]
            levelstext = " (warn, crit at %d/%d events)" % (warn, crit)
            if events >= crit:
                status = 2
            elif events >= warn:
                status = 1
            else:
                status = 0
            if status:
                infotext += levelstext
        else:
            status = 0
        return status, infotext

    def check_event_rate(event_type):
        events = parsed[event_type + "_events"]
        event_rate = get_rate(
            get_value_store(), event_type + "_events", now, events, raise_overflow=True
        )
        infotext = f"{event_rate:.2f} {event_type} events/s"
        if params.get(event_type + "_event_rate"):
            warn, crit = params[event_type + "_event_rate"]
            levelstext = f" (warn/crit at {warn:.2f}/{crit:.2f} 1/s)"
            perfdata = [(event_type + "event_rate", event_rate, warn, crit)]
            if event_rate >= crit:
                status = 2
            elif event_rate >= warn:
                status = 1
            else:
                status = 0
            if status:
                infotext += levelstext
        else:
            perfdata = [(event_type + "_event_rate", event_rate)]
            status = 0
        return status, infotext, perfdata

    yield check_events("critical")
    yield check_events("noncritical")
    yield check_event_rate("critical")
    yield check_event_rate("noncritical")


check_info["safenet_hsm.events"] = LegacyCheckDefinition(
    name="safenet_hsm_events",
    service_name="HSM Safenet Event Stats",
    sections=["safenet_hsm"],
    discovery_function=inventory_safenet_hsm_events,
    check_function=check_safenet_hsm_events,
    check_ruleset_name="safenet_hsm_eventstats",
    check_default_parameters={
        "critical_event_rate": (0.0001, 0.0005),
    },
)

# .
#   .--Operation stats-----------------------------------------------------.
#   |             ___                       _   _                          |
#   |            / _ \ _ __   ___ _ __ __ _| |_(_) ___  _ __               |
#   |           | | | | '_ \ / _ \ '__/ _` | __| |/ _ \| '_ \              |
#   |           | |_| | |_) |  __/ | | (_| | |_| | (_) | | | |             |
#   |            \___/| .__/ \___|_|  \__,_|\__|_|\___/|_| |_|             |
#   |                 |_|                                                  |
#   |                            _        _                                |
#   |                        ___| |_ __ _| |_ ___                          |
#   |                       / __| __/ _` | __/ __|                         |
#   |                       \__ \ || (_| | |_\__ \                         |
#   |                       |___/\__\__,_|\__|___/                         |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_safenet_hsm(parsed):
    if parsed:
        return [(None, {})]
    return []


def check_safenet_hsm(_no_item, params, parsed):
    now = time.time()

    def check_operation_request_rate(operation_requests):
        request_rate = get_rate(
            get_value_store(), "operation_requests", now, operation_requests, raise_overflow=True
        )

        status, infotext, extra_perf = check_levels(
            request_rate, "request_rate", params["request_rate"], unit="1/s", infoname="Requests"
        )
        perfdata = [("requests_per_second", request_rate)] + extra_perf[1:]
        return status, infotext, perfdata

    def check_operation_error_rate(operation_errors):
        error_rate = get_rate(
            get_value_store(), "operation_errors", now, operation_errors, raise_overflow=True
        )
        infotext = "%.2f operation errors/s" % error_rate
        if params.get("error_rate"):
            warn, crit = params["error_rate"]
            levelstext = f" (warn/crit at {warn:.2f}/{crit:.2f} 1/s)"
            perfdata = [("error_rate", error_rate, warn, crit)]
            if error_rate >= crit:
                status = 2
            elif error_rate >= warn:
                status = 1
            else:
                status = 0
            if status:
                infotext += levelstext
        else:
            perfdata = [("error_rate", error_rate)]
            status = 0
        return status, infotext, perfdata

    def check_operation_errors(operation_errors):
        infotext = "%d operation errors since last reset" % operation_errors
        if params.get("operation_errors"):
            warn, crit = params["operation_errors"]
            levelstext = " (warn, crit at %d/%d errors)" % (warn, crit)
            if operation_errors >= crit:
                status = 2
            elif operation_errors >= warn:
                status = 1
            else:
                status = 0
            if status:
                infotext += levelstext
        else:
            status = 0
        return status, infotext

    yield check_operation_request_rate(parsed["operation_requests"])
    yield check_operation_error_rate(parsed["operation_errors"])
    yield check_operation_errors(parsed["operation_errors"])


check_info["safenet_hsm"] = LegacyCheckDefinition(
    name="safenet_hsm",
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12383"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12383.3.1.1",
        oids=["1", "2", "3", "4"],
    ),
    parse_function=parse_safenet_hsm,
    service_name="HSM Operation Stats",
    discovery_function=inventory_safenet_hsm,
    check_function=check_safenet_hsm,
    check_ruleset_name="safenet_hsm_operstats",
    check_default_parameters={"error_rate": (0.01, 0.05), "request_rate": None},
)
