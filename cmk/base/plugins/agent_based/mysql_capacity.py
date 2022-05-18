#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# <<<mysql_capacity>>>
# greendb 163840  1428160512
# hirn    16384   238026752
# information_schema  9216    0
# mysql   650067  0
# performance_schema  0   0
# wa-confluence   15499264    13805551616

# new: can have instance headers (can be empty), e.g.:
# <<<mysql_capacity>>>
# [[]]
# information_schema      147456  0
# mysql   665902  292
# performance_schema      0       0
# test 409255936       54525952
from collections import defaultdict
from typing import Any, Mapping

from .agent_based_api.v1 import check_levels, register, render, Service
from .agent_based_api.v1.type_defs import CheckResult


def parse_mysql_capacity(string_table):
    item = "mysql"
    section: dict[str, dict[str, tuple]] = defaultdict(dict)
    for line in string_table:
        if line[0].startswith("[["):
            item = " ".join(line).strip("[ ]") or item
            continue
        dbname, size, avail = " ".join(line[:-2]), line[-2], line[-1]
        try:
            section[item][dbname] = (int(size), int(avail))
        except ValueError:
            section[item][dbname] = (size, avail)
    return section


register.agent_section(name="mysql_capacity", parse_function=parse_mysql_capacity)


def discover_mysql_size(section):
    for instance, data in section.items():
        for dbname, values in data.items():
            if (
                dbname not in ("information_schema", "mysql", "performance_schema")
                and "NULL" not in values
            ):
                yield Service(item=f"{instance}:{dbname}")


def check_mysql_size(item: str, params: Mapping[str, Any], section: Mapping) -> CheckResult:
    instance, dbname = item.split(":", 1)
    size, _avail = section.get(instance, {}).get(dbname, (None, None))
    if not isinstance(size, int):
        return

    # size and avail are given as bytes
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
    discovery_function=discover_mysql_size,
    check_function=check_mysql_size,
    check_ruleset_name="mysql_db_size",
    check_default_parameters={"levels": None},
)
