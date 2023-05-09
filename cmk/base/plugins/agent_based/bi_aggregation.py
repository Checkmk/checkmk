#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Dict
import ast

from cmk.base.check_api_utils import state_markers  # pylint: disable=cmk-module-layer-violation
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


def render_bi_infos(infos):
    if not infos:
        return None

    own_infos, nested_infos = infos
    lines = []
    if "error" in own_infos:
        lines.append("%s %s" %
                     (state_markers[own_infos["error"]["state"]], own_infos["error"]["output"]))
    if "custom" in own_infos:
        lines.append(own_infos["custom"]["output"])

    for nested_info in nested_infos:
        nested_lines = render_bi_infos(nested_info)
        for idx, line in enumerate(nested_lines):
            if idx == 0:
                lines.append("+-- %s" % line)
            else:
                lines.append("| %s" % line)

    return lines


def check_bi_aggregation(item: str, section: Section) -> CheckResult:
    bi_data = section.get(item)
    if not bi_data:
        return

    overall_state = bi_data["state_computed_by_agent"]
    yield Result(
        state=State(overall_state),
        summary="Aggregation state: %s" % ['Ok', 'Warning', 'Critical', 'Unknown'][overall_state],
    )

    yield Result(
        state=State.OK,
        summary="In downtime: %s" % ("yes" if bi_data["in_downtime"] else "no"),
    )
    yield Result(
        state=State.OK,
        summary="Acknowledged: %s" % ("yes" if bi_data["acknowledged"] else "no"),
    )

    if bi_data["infos"]:
        infos = ["", "Aggregation Errors"]
        infos.extend(render_bi_infos(bi_data["infos"]))
        yield Result(state=State.OK, notice="\n".join(infos))


register.check_plugin(
    name="bi_aggregation",
    service_name="Aggr %s",
    discovery_function=discover_bi_aggregation,
    check_function=check_bi_aggregation,
)
