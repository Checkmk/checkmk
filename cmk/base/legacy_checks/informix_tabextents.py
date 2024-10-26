#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO WATORule


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}


def parse_informix_tabextents(string_table):
    parsed = {}
    instance = None
    entry = None
    for line in string_table:
        if instance is not None and line == ["(constant)", "TABEXTENTS"]:
            entry = {}
            parsed.setdefault(instance, [])
            parsed[instance].append(entry)

        elif line[0].startswith("[[[") and line[0].endswith("]]]"):
            instance = line[0][3:-3]

        elif entry is not None:
            entry.setdefault(line[0], line[1])

    return parsed


def inventory_informix_tabextents(parsed):
    return [(instance, {}) for instance in parsed]


def check_informix_tabextents(item, params, parsed):
    if item in parsed:
        max_extents = -1
        long_output = []
        for entry in parsed[item]:
            max_extents = max(max_extents, int(entry["extents"]))
            long_output.append(
                "[{}/{}] Extents: {}, Rows: {}".format(
                    entry["db"], entry["tab"], entry["extents"], entry["nrows"]
                )
            )

        warn, crit = params["levels"]
        state = 0
        infotext = "Maximal extents: %s" % max_extents
        if max_extents >= crit:
            state = 2
        elif max_extents >= warn:
            state = 1
        if state:
            infotext += f" (warn/crit at {warn}/{crit})"
        return (
            state,
            "{}\n{}".format(infotext, "\n".join(long_output)),
            [("max_extents", max_extents)],
        )
    return None


check_info["informix_tabextents"] = LegacyCheckDefinition(
    name="informix_tabextents",
    parse_function=parse_informix_tabextents,
    service_name="Informix Table Extents %s",
    discovery_function=inventory_informix_tabextents,
    check_function=check_informix_tabextents,
    check_ruleset_name="informix_tabextents",
    check_default_parameters={
        "levels": (40, 70),
    },
)
