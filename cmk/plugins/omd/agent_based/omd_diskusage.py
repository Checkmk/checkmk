#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Final, LiteralString

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Service,
    StringTable,
)


@dataclass(frozen=True)
class Spec:
    metric_name: LiteralString
    label: LiteralString


@dataclass(frozen=True)
class Directory:
    value: int
    spec: Spec


Section = Mapping[str, Sequence[Directory]]


SPECS: Final = {
    "": Spec(metric_name="omd_size", label="Total"),
    "/var/log": Spec(metric_name="omd_log_size", label="Logs"),
    "/var/check_mk/rrd": Spec(metric_name="omd_rrd_size", label="RRDs"),
    "/tmp": Spec(metric_name="omd_tmp_size", label="Tmp"),  # nosec B108 # BNS:13b2c8
    "/local": Spec(metric_name="omd_local_size", label="Local"),
    "/var/check_mk/agents": Spec(metric_name="omd_agents_size", label="Agents"),
    "/var/mkeventd/history": Spec(metric_name="omd_history_size", label="History"),
    "/var/check_mk/core": Spec(metric_name="omd_core_size", label="Core"),
    "/var/pnp4nagios": Spec(metric_name="omd_pnp4nagios_size", label="PNP4Nagios"),
    "/var/check_mk/inventory_archive": Spec(
        metric_name="omd_inventory_size",
        label="Inventory",
    ),
    "/var/check_mk/crashes": Spec(metric_name="omd_crashes_size", label="Crashes"),
    "/var/check_mk/otel_collector": Spec(metric_name="omd_otel_collector_size", label="OTel"),
    "/var/clickhouse-server": Spec(metric_name="omd_metric_backend_size", label="Metric backend"),
}


def sub_section_parser(
    string_table: StringTable,
) -> Iterator[tuple[str, Sequence[tuple[int, str]]]]:
    sub_section: list[tuple[int, str]] = []
    name = ""
    for line in string_table:
        if line[0].startswith("[") and line[0].endswith("]"):
            if len(sub_section) == 0:
                name = line[0].removeprefix("[site ")[:-1]
                continue
            yield name, sub_section
            name = line[0].removeprefix("[site ")[:-1]
            sub_section = []
        elif line[0] != "":
            raw_value, dir_name = line[0].split()
            sub_section.append((int(raw_value), dir_name.rstrip("/")))
    if len(sub_section) != 0:
        yield name, sub_section


def parse(string_table: StringTable) -> Section:
    return {
        site_name: [
            Directory(spec=spec, value=size)
            for size, dir_name in lines
            if (spec := SPECS.get(dir_name.removeprefix(f"/omd/sites/{site_name}")))
        ]
        for site_name, lines in sub_section_parser(string_table)
    }


agent_section_omd_diskusage = AgentSection(
    name="omd_diskusage",
    parse_function=parse,
)


def discovery(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check(item: str, section: Section) -> CheckResult:
    if (directories := section.get(item)) is None:
        return

    for entry in sorted(directories, key=lambda d: (d.spec.label != "Total", d.spec.label)):
        yield from check_levels_v1(
            entry.value,
            metric_name=entry.spec.metric_name,
            label=entry.spec.label,
            render_func=render.bytes,
        )


check_plugin_omd_diskusage = CheckPlugin(
    name="omd_diskusage",
    service_name="OMD %s disk usage",
    discovery_function=discovery,
    check_function=check,
)
