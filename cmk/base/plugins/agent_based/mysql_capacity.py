#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections import defaultdict
from typing import Any, Mapping

from .agent_based_api.v1 import check_levels, register, render, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

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


register.agent_section(name="mysql_capacity", parse_function=parse_size)


def discover_capacity(section: Section) -> DiscoveryResult:
    for instance, databases in section.items():
        for dbname in databases:
            if dbname in ["information_schema", "performance_schema", "mysql"]:
                continue
            yield Service(item=f"{instance}:{dbname}")


def check_capacity(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    instance, dbname = item.split(":", 1)
    if (size := section.get(instance, {}).get(dbname, None)) is not None:
        yield from check_levels(
            size,
            metric_name="database_size",
            levels_upper=params["levels"],
            render_func=render.bytes,
            label="Size",
        )


register.check_plugin(
    name="mysql_capacity",
    service_name="MySQL DB Size %s",
    discovery_function=discover_capacity,
    check_function=check_capacity,
    check_ruleset_name="mysql_db_size",
    check_default_parameters={"levels": None},
)
