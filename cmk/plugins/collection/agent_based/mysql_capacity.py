#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections import defaultdict
from collections.abc import Mapping
from typing import Any

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

InstanceName = str
DBName = str
Section = Mapping[InstanceName, Mapping[DBName, int]]


def parse_size(string_table: StringTable) -> Section:
    item = "mysql"
    section: dict[InstanceName, dict[DBName, int]] = defaultdict(dict)
    for line in string_table:
        if line[0].startswith("[["):
            item = " ".join(line).strip("[ ]") or item
            continue
        dbname, size = " ".join(line[:-2]), line[-2]
        try:
            section[item][dbname] = int(size)
        except ValueError:
            pass
    return section


agent_section_mysql_capacity = AgentSection(name="mysql_capacity", parse_function=parse_size)


def discover_capacity(section: Section) -> DiscoveryResult:
    for instance, databases in section.items():
        for dbname in databases:
            if dbname in ["information_schema", "performance_schema", "mysql"]:
                continue
            yield Service(item=f"{instance}:{dbname}")


def check_capacity(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    instance, dbname = item.split(":", 1)
    if (size := section.get(instance, {}).get(dbname, None)) is not None:
        yield from check_levels_v1(
            size,
            metric_name="database_size",
            levels_upper=params["levels"],
            render_func=render.bytes,
            label="Size",
        )


check_plugin_mysql_capacity = CheckPlugin(
    name="mysql_capacity",
    service_name="MySQL DB Size %s",
    discovery_function=discover_capacity,
    check_function=check_capacity,
    check_ruleset_name="mysql_db_size",
    check_default_parameters={"levels": None},
)
