#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
from dataclasses import dataclass
from typing import Final, Iterator, LiteralString, Mapping, NewType, Sequence

from cmk.base.plugins.agent_based.agent_based_api.v1 import check_levels, register, render, Service
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)


@dataclass(frozen=True)
class Spec:
    metric_name: LiteralString
    path: LiteralString
    label: LiteralString


@dataclass(frozen=True)
class Directory:
    spec: Spec


@dataclass(frozen=True)
class DirectoryWithValue(Directory):
    value: int
    spec: Spec


@dataclass(frozen=True)
class Site:
    site: int
    entries: Sequence[Directory]


Section = NewType("Section", Mapping[str, Site])


SPECS: Final = [
    Spec(metric_name="omd_log_size", path="var/log", label="Logs"),
    Spec(metric_name="omd_rrd_size", path="var/check_mk/rrd", label="RRDs"),
    Spec(metric_name="omd_tmp_size", path="tmp/", label="Tmp"),
    Spec(metric_name="omd_local_size", path="local/", label="Local"),
    Spec(metric_name="omd_agents_size", path="var/check_mk/agents/", label="Agents"),
    Spec(metric_name="omd_history_size", path="var/mkeventd/history/", label="History"),
    Spec(metric_name="omd_core_size", path="var/check_mk/core/", label="Core"),
    Spec(metric_name="omd_pnp4nagios_size", path="/var/pnp4nagios/", label="PNP4Nagios"),
    Spec(
        metric_name="omd_inventory_size", path="var/check_mk/inventory_archive/", label="Inventory"
    ),
]


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


def _parse_line(spec: Spec, line: str) -> Directory:
    if "No such file" in line:
        return Directory(spec=spec)
    return DirectoryWithValue(spec=spec, value=int(line.split()[0]))


def parse(string_table: StringTable) -> Section:
    sites: dict[str, Site] = {}
    for section_name, lines in sub_section_parser(string_table):
        entries = []
        for line in lines:
            if spec := next((spec for spec in SPECS if spec.path in line), None):
                entries.append(_parse_line(spec, line))
            else:
                site = int(line.split()[0])
            sites[section_name.split()[1]] = Site(site, entries)
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
    for entry in sorted(site.entries, key=lambda x: x.spec.label):
        yield from check_levels(
            entry.value if isinstance(entry, DirectoryWithValue) else 0,
            metric_name=entry.spec.metric_name,
            label=entry.spec.label,
            render_func=render.bytes,
        )


register.check_plugin(
    name="omd_diskusage",
    service_name="OMD %s disk usage",
    discovery_function=discovery,
    check_function=check,
)
