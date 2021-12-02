#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from time import time
from typing import Mapping, Optional, Tuple

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    check_levels,
    register,
    render,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils.k8s import PodConditions


def parse(string_table: StringTable) -> PodConditions:
    """Parses `string_table` into a PodConditions instance"""
    return PodConditions(**json.loads(string_table[0][0]))


def discovery(section: PodConditions) -> DiscoveryResult:
    yield Service()


def check(
    params: Mapping[str, Optional[Tuple[float, float]]], section: PodConditions
) -> CheckResult:
    curr_timestamp = int(time())
    for name, value in section:
        if value.status:
            yield Result(state=State.OK, summary=f"{name.title()} condition passed")
            continue
        time_diff = curr_timestamp - value.last_transition_time
        summary = f"{name.title()} condition not passed ({value.reason}: {value.detail}) for {{}}"
        for result in check_levels(
            time_diff, levels_upper=params.get(name), render_func=render.timespan
        ):
            yield Result(state=result.state, summary=summary.format(result.summary))


register.agent_section(
    name="k8s_pod_conditions_v1",
    parsed_section_name="k8s_pod_conditions",
    parse_function=parse,
)

register.check_plugin(
    name="k8s_pod_conditions",
    service_name="Pod Condition",
    discovery_function=discovery,
    check_function=check,
    check_default_parameters={},
    check_ruleset_name="k8s_pod_conditions",
)
