#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition

check_info = {}


def parse_informix_locks(string_table):
    parsed = {}
    instance = None
    for line in string_table:
        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            instance = line[0][3:-3]

        elif instance is not None and line[0] == "LOCKS":
            parsed.setdefault(instance, {"locks": line[1], "type": line[2]})

    return parsed


def discover_informix_locks(parsed):
    return [(instance, {}) for instance in parsed]


def check_informix_locks(item, params, parsed):
    if item in parsed:
        data = parsed[item]
        locks = int(data["locks"])
        warn, crit = params["levels"]

        return check_levels(locks, "locks", (warn, crit), infoname=f"Type: {data['type']}, Locks")
    return None


check_info["informix_locks"] = LegacyCheckDefinition(
    name="informix_locks",
    parse_function=parse_informix_locks,
    service_name="Informix Locks %s",
    discovery_function=discover_informix_locks,
    check_function=check_informix_locks,
    check_ruleset_name="informix_locks",
    check_default_parameters={
        "levels": (70, 80),
    },
)
