#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import cast, Literal, Mapping, Optional, Tuple, Union

from cmk.base.plugins.agent_based.agent_based_api.v1 import check_levels, register, Service
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils.kube import ContainerCount

OptionalLevels = Union[Literal["no_levels"], Tuple[Literal["levels"], Tuple[int, int]]]
KubeContainersLevelsUpperLower = Mapping[str, OptionalLevels]
CountName = Literal["running", "waiting", "terminated", "total"]


def parse(string_table: StringTable) -> ContainerCount:
    """Parses running, waiting and terminated containers into ContainerCount"""
    return ContainerCount(**json.loads(string_table[0][0]))


def discovery(section: ContainerCount) -> DiscoveryResult:
    yield Service()


def check(params: KubeContainersLevelsUpperLower, section: ContainerCount) -> CheckResult:
    """Computes `total` and uses `check_levels` for each section element,
    setting levels from `params` individually"""
    section_dict = section.dict()
    section_dict["total"] = sum(section_dict.values())
    for name, value in section_dict.items():
        level_count_name = cast(CountName, name)
        yield from check_levels(
            value,
            levels_upper=_get_levels(params, level_count_name, "upper"),
            levels_lower=_get_levels(params, level_count_name, "lower"),
            metric_name=f"kube_node_container_count_{name}",
            label=f"{name.title()}",
        )


def _get_levels(
    params: KubeContainersLevelsUpperLower,
    name: CountName,
    level_name: Literal["upper", "lower"],
) -> Optional[Tuple[int, int]]:
    level = params.get(f"{name}_{level_name}", "no_levels")
    if level == "no_levels":
        return None
    return level[1]


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
