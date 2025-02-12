#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import render

"""
Relevant documentation:
    * https://docs.deistercloud.com/content/Databases.30/IBM%20Informix.2/Monitoring.10.xml?embedded=true#51cf1eb453b73e7ffdd2172551fc58ed
    * https://www.ibm.com/docs/en/informix-servers/14.10?topic=tables-syschunks
"""

check_info = {}


def parse_informix_dbspaces(string_table):
    parsed = {}
    instance = None
    entry = None
    for line in string_table:
        if (
            instance is not None
            and len(line) > 2
            and line[0] == "(expression)"
            and line[2] == "DBSPACE"
        ):
            entry = {}
            ts = f"{instance} {line[1]}"
            parsed.setdefault(ts, [])
            parsed[ts].append(entry)

        elif line[0].startswith("[[[") and line[0].endswith("]]]"):
            instance = line[0][3:-3]

        elif entry is not None:
            entry.setdefault(line[0], "".join(line[1:]))

    return parsed


def inventory_informix_dbspaces(parsed):
    return [(ts, {}) for ts in parsed]


def check_informix_dbspaces(item, params, parsed):
    if item in parsed:
        datafiles = parsed[item]
        size = 0
        free = 0
        for entry in datafiles:
            pagesize = int(entry["pagesize"])
            free += int(entry["nfree"]) * pagesize
            size += int(entry["chksize"]) * pagesize

        used = size - free
        infotext = f"Data files: {len(datafiles)}, Size: {render.disksize(size)}, Used: {render.disksize(used)}"
        state = 0
        if "levels" in params:
            warn, crit = params["levels"]
            if size >= crit:
                state = 2
            elif size >= warn:
                state = 1
            if state:
                infotext += f" (warn/crit at {render.disksize(warn)}/{render.disksize(crit)})"

        yield state, infotext, [("tablespace_size", size), ("tablespace_used", used)]

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


check_info["informix_dbspaces"] = LegacyCheckDefinition(
    name="informix_dbspaces",
    parse_function=parse_informix_dbspaces,
    service_name="Informix Tablespace %s",
    discovery_function=inventory_informix_dbspaces,
    check_function=check_informix_dbspaces,
    check_ruleset_name="informix_dbspaces",
    check_default_parameters={"levels_perc": (80.0, 85.0)},
)
