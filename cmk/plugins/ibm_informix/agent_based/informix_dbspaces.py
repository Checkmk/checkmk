#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Relevant documentation:
    * https://docs.deistercloud.com/content/Databases.30/IBM%20Informix.2/Monitoring.10.xml?embedded=true#51cf1eb453b73e7ffdd2172551fc58ed
    * https://www.ibm.com/docs/en/informix-servers/14.10?topic=tables-syschunks
"""

from collections.abc import Mapping
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.rulesets.v1.form_specs import SimpleLevelsConfigModel

FLAG_BLOBSPACE = 512
ParsedSubsection = dict[str, str]
ParsedSection = dict[str, list[ParsedSubsection]]


class CheckParams(TypedDict):
    levels: SimpleLevelsConfigModel[int]
    levels_perc: SimpleLevelsConfigModel[float]


def parse_informix_dbspaces(string_table: StringTable) -> ParsedSection:
    parsed: ParsedSection = {}
    instance = None
    entry: ParsedSubsection | None = None
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


def discovery_informix_dbspaces(section: ParsedSection) -> DiscoveryResult:
    yield from [Service(item=ts) for ts in section]


def _get_pagesize(entry: Mapping[str, str]) -> tuple[int, int]:
    pagesize = int(entry["pagesize"])
    system_pagesize = int(entry["system_pagesize"])
    nfree_pagesize = pagesize if FLAG_BLOBSPACE & int(entry["chunk_flags"]) else system_pagesize

    return system_pagesize, nfree_pagesize


def check_informix_dbspaces(item: str, params: CheckParams, section: ParsedSection) -> CheckResult:
    if item in section:
        datafiles = section[item]
        size = 0
        free = 0
        for entry in datafiles:
            system_pagesize, nfree_pagesize = _get_pagesize(entry)
            # FYI: The reference page size for nfree depends on the type of space
            free += int(entry["nfree"]) * nfree_pagesize
            size += int(entry["chksize"]) * system_pagesize

        used = size - free
        levels_used = params["levels_perc"]
        if levels_used[0] == "fixed":
            levels_used = (
                "fixed",
                (levels_used[1][0] * size / 100.0, levels_used[1][1] * size / 100.0),
            )

        yield Result(state=State.OK, summary=f"Data files: {len(datafiles)}")
        yield from check_levels(
            value=size,
            metric_name="tablespace_size",
            levels_upper=params["levels"],
            render_func=lambda x: f"Size: {render.disksize(x)}",
        )
        yield from check_levels(
            value=used,
            metric_name="tablespace_used",
            levels_upper=levels_used,
            render_func=lambda x: f"Used: {render.disksize(x)}",
        )


agent_section_informix_dbspaces = AgentSection(
    name="informix_dbspaces",
    parse_function=parse_informix_dbspaces,
)


check_plugin_informix_dbspaces = CheckPlugin(
    name="informix_dbspaces",
    service_name="Informix Tablespace %s",
    discovery_function=discovery_informix_dbspaces,
    check_function=check_informix_dbspaces,
    check_ruleset_name="informix_dbspaces",
    check_default_parameters=CheckParams(
        levels=("no_levels", None), levels_perc=("fixed", (80.0, 85.0))
    ),
)
