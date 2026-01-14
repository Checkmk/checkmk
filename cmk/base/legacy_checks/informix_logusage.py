#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"

# mypy: disable-error-code="no-untyped-def"


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
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


def discover_informix_logusage(parsed):
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

        yield check_levels(
            logfiles,
            "file_count",
            None,
            infoname="Files",
            human_readable_func=str,
        )
        yield check_levels(
            size,
            "log_files_total",
            params.get("levels"),
            infoname="Size",
            human_readable_func=render.bytes,
        )
        yield check_levels(
            used,
            "log_files_used",
            None,
            infoname="Used",
            human_readable_func=render.bytes,
        )

        if not size:
            return

        yield check_levels(
            used * 100.0 / size,
            "log_files_used_perc",
            params["levels_perc"],
            infoname="Usage",
            human_readable_func=render.percent,
        )


check_info["informix_logusage"] = LegacyCheckDefinition(
    name="informix_logusage",
    parse_function=parse_informix_logusage,
    service_name="Informix Log Usage %s",
    discovery_function=discover_informix_logusage,
    check_function=check_informix_logusage,
    check_ruleset_name="informix_logusage",
    check_default_parameters={"levels_perc": (80.0, 85.0)},
)
