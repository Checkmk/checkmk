#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Tuple, TypedDict

from cmk.base.plugins.agent_based.agent_based_api.v1 import check_levels, register, Service
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils.k8s import ContainerCount


class LevelsUpperLower(TypedDict, total=False):
    levels_upper: Tuple[int, int]
    levels_lower: Tuple[int, int]


class K8sContainersLevelsUpperLower(TypedDict, total=False):
    running: LevelsUpperLower
    waiting: LevelsUpperLower
    terminated: LevelsUpperLower
    total: LevelsUpperLower


def parse(string_table: StringTable) -> ContainerCount:
    """Parses running, waiting and terminated containers into ContainerCount"""
    return ContainerCount(**json.loads(string_table[0][0]))


def discovery(section: ContainerCount) -> DiscoveryResult:
    yield Service()


def check(params: K8sContainersLevelsUpperLower, section: ContainerCount) -> CheckResult:
    """Computes `total` and uses `check_levels` for each section element,
    setting levels from `params` individually"""
    section_dict = section.dict()
    section_dict["total"] = sum(section_dict.values())
    for name, value in section_dict.items():
        levels = params.get(name, {})
        assert isinstance(levels, dict)
        yield from check_levels(
            value,
            levels_upper=levels.get("levels_upper"),
            levels_lower=levels.get("levels_lower"),
            metric_name=f"kube_node_container_count_{name}",
            label=f"{name.title()}",
        )


register.agent_section(
    name="kube_node_container_count_v1",
    parsed_section_name="kube_node_container_count",
    parse_function=parse,
)

register.check_plugin(
    name="kube_node_container_count",
    service_name="Containers",
    discovery_function=discovery,
    check_function=check,
    check_ruleset_name="kube_node_container_count",
    check_default_parameters={},
)
