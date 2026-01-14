#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# TODO WATO


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition

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


def discover_informix_sessions(parsed):
    return [(instance, {}) for instance in parsed]


def check_informix_sessions(item, params, parsed):
    if item in parsed:
        sessions = int(parsed[item])
        warn, crit = params["levels"]

        return check_levels(sessions, "sessions", (warn, crit), infoname="Sessions")
    return None


check_info["informix_sessions"] = LegacyCheckDefinition(
    name="informix_sessions",
    parse_function=parse_informix_sessions,
    service_name="Informix Sessions %s",
    discovery_function=discover_informix_sessions,
    check_function=check_informix_sessions,
    check_ruleset_name="informix_sessions",
    check_default_parameters={"levels": (50, 60)},
)
