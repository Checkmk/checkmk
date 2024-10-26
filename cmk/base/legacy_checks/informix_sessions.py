#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO WATO


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}


def parse_informix_sessions(string_table):
    parsed = {}
    instance = None
    for line in string_table:
        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            instance = line[0][3:-3]

        elif instance is not None and line[0] == "SESSIONS":
            parsed.setdefault(instance, line[1])

    return parsed


def inventory_informix_sessions(parsed):
    return [(instance, {}) for instance in parsed]


def check_informix_sessions(item, params, parsed):
    if item in parsed:
        sessions = int(parsed[item])
        warn, crit = params["levels"]
        state = 0
        infotext = "%s sessions" % sessions
        if sessions >= crit:
            state = 2
        elif sessions >= warn:
            state = 0
        if state:
            infotext += f" (warn/crit at {warn}/{crit})"
        return state, infotext, [("sessions", sessions)]
    return None


check_info["informix_sessions"] = LegacyCheckDefinition(
    name="informix_sessions",
    parse_function=parse_informix_sessions,
    service_name="Informix Sessions %s",
    discovery_function=inventory_informix_sessions,
    check_function=check_informix_sessions,
    check_ruleset_name="informix_sessions",
    check_default_parameters={"levels": (50, 60)},
)
