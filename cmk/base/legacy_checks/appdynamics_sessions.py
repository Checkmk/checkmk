#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="arg-type"
# mypy: disable-error-code="no-untyped-def"

# <<<appdynamics_sessions:sep(124)>>>
# Hans|/hans|rejectedSessions:0|sessionAverageAliveTime:1800|sessionCounter:13377|expiredSessions:13371|processingTime:1044|maxActive:7|activeSessions:6|sessionMaxAliveTime:4153


import time

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import get_rate, get_value_store, StringTable

check_info = {}


def discover_appdynamics_sessions(info):
    for line in info:
        yield " ".join(line[0:2]), {}


def check_appdynamics_sessions(item, params, info):
    for line in info:
        if item == " ".join(line[0:2]):
            values = {}
            for metric in line[2:]:
                name, value = metric.split(":")
                values[name] = int(value)

            active = values["activeSessions"]
            rejected = values["rejectedSessions"]
            max_active = values["maxActive"]
            counter = values["sessionCounter"]

            now = time.time()
            rate_id = "appdynamics_sessions.%s.counter" % (item.lower().replace(" ", "_"))
            counter_rate = get_rate(get_value_store(), rate_id, now, counter, raise_overflow=True)

            yield check_levels(
                active,
                "running_sessions",
                (params["levels_upper"] or (None, None)) + (params["levels_lower"] or (None, None)),
                human_readable_func=str,
                infoname="Running sessions",
            )

            yield check_levels(counter_rate, None, None, human_readable_func=lambda x: f"{x}/sec")

            yield check_levels(
                rejected, "rejected_sessions", None, human_readable_func=str, infoname="Rejected"
            )

            yield 0, "Maximum active: %d" % max_active


def parse_appdynamics_sessions(string_table: StringTable) -> StringTable:
    return string_table


check_info["appdynamics_sessions"] = LegacyCheckDefinition(
    name="appdynamics_sessions",
    parse_function=parse_appdynamics_sessions,
    service_name="AppDynamics Sessions %s",
    discovery_function=discover_appdynamics_sessions,
    check_function=check_appdynamics_sessions,
    check_ruleset_name="jvm_sessions",
    check_default_parameters={
        "levels_lower": None,
        "levels_upper": None,
    },
)
