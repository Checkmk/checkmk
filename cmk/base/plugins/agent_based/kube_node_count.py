#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from typing import Literal, Tuple, TypedDict

from .agent_based_api.v1 import check_levels, register, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.k8s import NodeCount


class K8sNodeCountLevelsVSResult(TypedDict, total=False):
    levels_upper: Tuple[int, int]
    levels_lower: Tuple[int, int]


class K8sNodeCountVSResult(TypedDict, total=False):
    worker: K8sNodeCountLevelsVSResult
    control_plane: K8sNodeCountLevelsVSResult


def parse(string_table: StringTable) -> NodeCount:
    return NodeCount(**json.loads(string_table[0][0]))


def discovery(section: NodeCount) -> DiscoveryResult:
    yield Service()


def _check_levels(
    value: int, name: Literal["worker", "control_plane"], params: K8sNodeCountVSResult
) -> CheckResult:
    levels_upper = None
    levels_lower = None
    if name in params:
        levels_upper = params[name].get("levels_upper")
        levels_lower = params[name].get("levels_lower")
    yield from check_levels(
        value,
        metric_name=f"k8s_node_count_{name}",
        levels_upper=levels_upper,
        levels_lower=levels_lower,
        render_func=lambda x: str(int(x)),
        label=f"Number of {name.replace('_', ' ')} nodes",
        boundaries=(0, None),
    )


def check(params: K8sNodeCountVSResult, section: NodeCount) -> CheckResult:
    yield from _check_levels(section.worker, "worker", params)
    yield from _check_levels(section.control_plane, "control_plane", params)


register.agent_section(
    name="kube_node_count_v1",
    parse_function=parse,
    parsed_section_name="kube_node_count",
)

check_default_parameters: K8sNodeCountVSResult = {
    "worker": {"levels_lower": (3, 1)},
    "control_plane": {"levels_lower": (3, 1)},
}

register.check_plugin(
    name="kube_node_count",
    service_name="Node Count",
    discovery_function=discovery,
    check_function=check,
    check_ruleset_name="k8s_node_count",
    check_default_parameters=check_default_parameters,
)
