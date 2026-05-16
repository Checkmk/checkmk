#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, Sequence[Mapping[str, str]]]


def parse_informix_logusage(string_table: StringTable) -> Section:
    parsed: dict[str, list[dict[str, str]]] = {}
    instance: str | None = None
    entry: dict[str, str] | None = None
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


def discover_informix_logusage(section: Section) -> DiscoveryResult:
    for instance in section:
        yield Service(item=instance)


def check_informix_logusage(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if item not in section:
        return
    data = section[item]
    logfiles = len(data)
    if not logfiles:
        yield Result(state=State.WARN, summary="Log information missing")
        return

    size = 0
    used = 0
    for entry in data:
        pagesize = int(entry["sh_pagesize"])
        size += int(entry["size"]) * pagesize
        used += int(entry["used"]) * pagesize

    yield from check_levels_v1(
        logfiles,
        metric_name="file_count",
        label="Files",
        render_func=str,
    )
    yield from check_levels_v1(
        size,
        metric_name="log_files_total",
        levels_upper=params.get("levels"),
        label="Size",
        render_func=render.bytes,
    )
    yield from check_levels_v1(
        used,
        metric_name="log_files_used",
        label="Used",
        render_func=render.bytes,
    )

    if not size:
        return

    yield from check_levels_v1(
        used * 100.0 / size,
        metric_name="log_files_used_perc",
        levels_upper=params["levels_perc"],
        label="Usage",
        render_func=render.percent,
    )


agent_section_informix_logusage = AgentSection(
    name="informix_logusage",
    parse_function=parse_informix_logusage,
)


check_plugin_informix_logusage = CheckPlugin(
    name="informix_logusage",
    service_name="Informix Log Usage %s",
    discovery_function=discover_informix_logusage,
    check_function=check_informix_logusage,
    check_ruleset_name="informix_logusage",
    check_default_parameters={"levels_perc": (80.0, 85.0)},
)
