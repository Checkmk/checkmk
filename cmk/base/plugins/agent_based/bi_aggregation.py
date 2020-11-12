#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Dict
import ast

from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .agent_based_api.v1 import register, Result, State, Service

Section = Dict[str, Any]


def parse_bi_aggregation(string_table: StringTable) -> Section:
    parsed = {}
    for line in string_table:
        parsed.update(ast.literal_eval(line[0]))
    return parsed


register.agent_section(
    name="bi_aggregation",
    parse_function=parse_bi_aggregation,
)


def discover_bi_aggregation(section: Section) -> DiscoveryResult:
    for aggr_name in section:
        yield Service(item=aggr_name)


def check_bi_aggregation(item: str, section: Section) -> CheckResult:
    bi_data = section.get(item)
    if not bi_data:
        return

    aggr_state = bi_data["aggr_state"]

    overall_state = aggr_state["state_computed_by_agent"]
    yield Result(
        state=State(overall_state),
        summary="Aggregation state: %s" % ['Ok', 'Warning', 'Critical', 'Unknown'][overall_state],
    )

    yield Result(
        state=State.OK,
        summary="In downtime: %s" % ("yes" if aggr_state.get("in_downtime") else "no"),
    )
    yield Result(
        state=State.OK,
        summary="Acknowledged: %s" % ("yes" if aggr_state.get("acknowledged") else "no"),
    )


register.check_plugin(
    name="bi_aggregation",
    service_name="Aggr %s",
    discovery_function=discover_bi_aggregation,
    check_function=check_bi_aggregation,
)
