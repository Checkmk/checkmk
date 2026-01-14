#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}


def parse_informix_status(string_table):
    parsed = {}
    instance = None
    for line in string_table:
        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            instance = line[0][3:-3]

        elif instance is not None and len(line) >= 2:
            stripped_line = [x.strip() for x in line]
            parsed.setdefault(instance, {})
            parsed[instance].setdefault(stripped_line[0], " ".join(stripped_line[1:]))

    return parsed


def discover_informix_status(parsed):
    return [(instance, {}) for instance in parsed]


def check_informix_status(item, params, parsed):
    map_states = {
        "0": (0, "initialization"),
        "1": (1, "quiescent"),
        "2": (1, "recovery"),
        "3": (1, "backup"),
        "4": (2, "shutdown"),
        "5": (0, "online"),
        "6": (1, "abort"),
        "7": (1, "single user"),
        "-1": (2, "offline"),
        "255": (2, "offline"),
    }

    if item in parsed:
        data = parsed[item]
        state, state_readable = map_states[data["Status"]]
        infotext = "Status: %s" % state_readable

        server_version = data.get("Server Version")
        if server_version:
            infotext += ", Version: %s" % server_version

        port = data.get("PORT")
        if port:
            infotext += ", Port: %s" % port.split(" ")[1]
        return state, infotext
    return None


check_info["informix_status"] = LegacyCheckDefinition(
    name="informix_status",
    parse_function=parse_informix_status,
    service_name="Informix Instance %s",
    discovery_function=discover_informix_status,
    check_function=check_informix_status,
)
