#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import re
from typing import Literal, Mapping, Optional, Tuple, Union

from .agent_based_api.v1 import check_levels, Metric, register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.kube import NodeCount, ReadyCount

OptionalLevels = Union[Literal["no_levels"], Tuple[Literal["levels"], Tuple[int, int]]]


KubeNodeCountVSResult = Mapping[str, OptionalLevels]


def parse(string_table: StringTable) -> NodeCount:
    return NodeCount(**json.loads(string_table[0][0]))


def discovery(section: NodeCount) -> DiscoveryResult:
    yield Service()


def _get_levels(
    params: KubeNodeCountVSResult,
    name: Literal["worker", "control_plane"],
    level_name: Literal["levels_lower", "levels_upper"],
) -> Optional[Tuple[int, int]]:
    level = params.get(f"{name}_{level_name}", "no_levels")
    if level == "no_levels":
        return None
    return level[1]


def _check_levels(
    ready_count: ReadyCount, name: Literal["worker", "control_plane"], params: KubeNodeCountVSResult
) -> CheckResult:
    levels_upper = _get_levels(params, name, "levels_upper")
    levels_lower = _get_levels(params, name, "levels_lower")
    result, metric = check_levels(
        ready_count.ready,
        metric_name=f"kube_node_count_{name}_ready",
        levels_upper=levels_upper,
        levels_lower=levels_lower,
        render_func=lambda x: str(int(x)),
        label=f"{name.replace('_', ' ')} nodes".capitalize(),
        boundaries=(0, None),
    )
    assert isinstance(result, Result)
    levels = ""
    # if '(warn/crit below 3/1)' is part of the summary, append it to our summary
    if match := re.match(r"[^(]+(\([^)]+\))", result.summary):
        levels = " " + match.groups()[0]

    yield Result(
        state=result.state,
        summary=f"{name.replace('_', ' ').capitalize()} nodes {ready_count.ready}/{ready_count.total}{levels}",
    )
    yield metric
    yield Metric(f"kube_node_count_{name}_not_ready", ready_count.not_ready)
    yield Metric(f"kube_node_count_{name}_total", ready_count.total)


def check(params: KubeNodeCountVSResult, section: NodeCount) -> CheckResult:
    yield from _check_levels(section.worker, "worker", params)
    if section.control_plane.total == 0:
        yield Result(state=State.OK, summary="No control plane nodes found")
    else:
        yield from _check_levels(section.control_plane, "control_plane", params)


register.agent_section(
    name="kube_node_count_v1",
    parse_function=parse,
    parsed_section_name="kube_node_count",
)

check_default_parameters: KubeNodeCountVSResult = {}

register.check_plugin(
    name="kube_node_count",
    service_name="Nodes",
    discovery_function=discovery,
    check_function=check,
    check_ruleset_name="kube_node_count",
    check_default_parameters=check_default_parameters,
)
