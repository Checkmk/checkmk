#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import render

check_info = {}


def parse_informix_logusage(string_table):
    parsed = {}
    instance = None
    entry = None
    for line in string_table:
        if instance is not None and line == ["(constant)", "LOGUSAGE"]:
            entry = {}
            parsed.setdefault(instance, [])
            parsed[instance].append(entry)

        elif line[0].startswith("[[[") and line[0].endswith("]]]"):
            instance = line[0][3:-3]

        elif entry is not None:
            if line[0] == "(expression)":
                k, v = line[1].split(":")
            else:
                k, v = line[0], line[1]
            entry.setdefault(k, v)

    return parsed


def inventory_informix_logusage(parsed):
    return [(instance, {}) for instance in parsed]


def check_informix_logusage(item, params, parsed):
    if item in parsed:
        data = parsed[item]
        logfiles = len(data)
        if not logfiles:
            yield 1, "Log information missing"
            return

        size = 0
        used = 0
        for entry in data:
            pagesize = int(entry["sh_pagesize"])
            size += int(entry["size"]) * pagesize
            used += int(entry["used"]) * pagesize

        infotext = f"Files: {logfiles}, Size: {render.bytes(size)}, Used: {render.bytes(used)}"
        state = 0
        if "levels" in params:
            warn, crit = params["levels"]
            if size >= crit:
                state = 2
            elif size >= warn:
                state = 1
            if state:
                infotext += f" (warn/crit at {render.bytes(warn)}/{render.bytes(crit)})"

        yield (
            state,
            infotext,
            [
                ("file_count", logfiles),
                ("log_files_total", size),
                ("log_files_used", used),
            ],
        )

        if size:
            used_perc = used * 100.0 / size
            infotext = "%.2f%%" % used_perc
            warn_perc, crit_perc = params["levels_perc"]
            state = 0
            if used_perc >= crit_perc:
                state = 2
            elif used_perc >= warn_perc:
                state = 1
            if state:
                infotext += f" (warn/crit at {warn_perc:.2f}%/{crit_perc:.2f}%)"

            yield state, infotext


check_info["informix_logusage"] = LegacyCheckDefinition(
    name="informix_logusage",
    parse_function=parse_informix_logusage,
    service_name="Informix Log Usage %s",
    discovery_function=inventory_informix_logusage,
    check_function=check_informix_logusage,
    check_ruleset_name="informix_logusage",
    check_default_parameters={"levels_perc": (80.0, 85.0)},
)
