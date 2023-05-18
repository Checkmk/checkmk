#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info


def parse_informix_locks(info):
    parsed = {}
    instance = None
    for line in info:
        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            instance = line[0][3:-3]

        elif instance is not None and line[0] == "LOCKS":
            parsed.setdefault(instance, {"locks": line[1], "type": line[2]})

    return parsed


def inventory_informix_locks(parsed):
    return [(instance, {}) for instance in parsed]


def check_informix_locks(item, params, parsed):
    if item in parsed:
        data = parsed[item]
        locks = int(data["locks"])
        warn, crit = params["levels"]
        state = 0
        infotext = "Type: %s, Locks: %s" % (data["type"], locks)
        if locks >= crit:
            state = 2
        elif locks >= crit:
            state = 1
        if state:
            infotext += " (warn/crit at %s/%s)" % (warn, crit)
        return state, infotext, [("locks", locks)]
    return None


check_info["informix_locks"] = LegacyCheckDefinition(
    parse_function=parse_informix_locks,
    discovery_function=inventory_informix_locks,
    check_function=check_informix_locks,
    service_name="Informix Locks %s",
    check_ruleset_name="informix_locks",
    check_default_parameters={
        "levels": (70, 80),
    },
)
