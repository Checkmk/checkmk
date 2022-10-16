#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ported by (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>
import ast
from typing import Any, Dict, Mapping

from .agent_based_api.v1 import get_value_store, register, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_LEVELS

Section = Dict[str, Mapping[str, Any]]


def parse_prism_container(string_table: StringTable) -> Section:
    parsed: Section = {}
    data = ast.literal_eval(string_table[0][0])
    for element in data.get("entities"):
        parsed.setdefault(element.get("name", "unknown"), element)
    return parsed


register.agent_section(
    name="prism_containers",
    parse_function=parse_prism_container,
)


def discovery_prism_container(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_prism_container(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    value_store = get_value_store()
    data = section.get(item)
    if not data:
        return

    capacity, freebytes = map(
        int,
        (
            data["usage_stats"].get("storage.user_capacity_bytes", 0),
            data["usage_stats"].get("storage.user_free_bytes", 0),
        ),
    )

    yield from df_check_filesystem_single(
        value_store,
        item,
        capacity / 1024**2,
        freebytes / 1024**2,
        0,
        None,
        None,
        params=params,
    )


register.check_plugin(
    name="prism_containers",
    service_name="NTNX Container %s",
    sections=["prism_containers"],
    check_default_parameters=FILESYSTEM_DEFAULT_LEVELS,
    discovery_function=discovery_prism_container,
    check_function=check_prism_container,
    check_ruleset_name="filesystem",
)
