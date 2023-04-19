#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
from dataclasses import dataclass
from typing import Iterator, Mapping, NewType, Sequence

from cmk.base.plugins.agent_based.agent_based_api.v1 import check_levels, register, render, Service
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)


@dataclass(frozen=True)
class Site:
    site: int
    logs: int
    rrds: int


Section = NewType("Section", Mapping[str, Site])


def sub_section_parser(string_table: StringTable) -> Iterator[tuple[str, Sequence[str]]]:
    sub_section: list[str] = []
    name = ""
    for line in string_table:
        if line[0].startswith("[") and line[0].endswith("]"):
            if len(sub_section) == 0:
                name = line[0][1:-1]
                continue
            yield name, sub_section
            name = line[0][1:-1]
            sub_section = []
        elif line[0] != "":
            sub_section.append(line[0])
    if len(sub_section) != 0:
        yield name, sub_section


def parse(string_table: StringTable) -> Section:
    sites: dict[str, Site] = {}
    for section_name, lines in sub_section_parser(string_table):
        log = rrd = site = 0
        for line in lines:
            if "log" in line:
                log = int(line.split()[0])
            elif "rrd" in line:
                rrd = int(line.split()[0])
            else:
                site = int(line.split()[0])
            sites[section_name.split()[1]] = Site(site, log, rrd)
    return Section(sites)


register.agent_section(
    name="omd_diskusage",
    parse_function=parse,
)


def discovery(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check(item: str, section: Section) -> CheckResult:
    site = section[item]
    yield from check_levels(
        site.site, metric_name="omd_size", label="Total", render_func=render.bytes
    )
    yield from check_levels(
        site.logs, metric_name="omd_log_size", label="Logs", render_func=render.bytes
    )
    yield from check_levels(
        site.rrds, metric_name="omd_rrd_size", label="RRDs", render_func=render.bytes
    )


register.check_plugin(
    name="omd_diskusage",
    service_name="OMD %s disk usage",
    discovery_function=discovery,
    check_function=check,
)
