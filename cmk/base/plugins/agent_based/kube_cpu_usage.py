#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Optional

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, Service
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils.kube_resources import (
    check_resource,
    DEFAULT_PARAMS,
    Params,
    parse_resources,
    Resources,
    Usage,
)


def parse_kube_performance_cpu_v1(string_table: StringTable) -> Usage:
    """Parses usage value into Usage"""
    return Usage(**json.loads(string_table[0][0]))


register.agent_section(
    name="kube_performance_cpu_usage_v1",
    parsed_section_name="kube_performance_cpu",
    parse_function=parse_kube_performance_cpu_v1,
)


def discovery_kube_cpu(
    section_kube_performance_cpu: Optional[Usage],
    section_kube_cpu_resources: Optional[Resources],
) -> DiscoveryResult:
    yield Service()


def check_kube_cpu(
    params: Params,
    section_kube_performance_cpu: Optional[Usage],
    section_kube_cpu_resources: Optional[Resources],
) -> CheckResult:
    assert section_kube_cpu_resources is not None
    yield from check_resource(
        params,
        section_kube_performance_cpu,
        section_kube_cpu_resources,
        "cpu",
        lambda x: f"{x:0.3f}",
    )


register.agent_section(
    name="kube_cpu_resources_v1",
    parsed_section_name="kube_cpu_resources",
    parse_function=parse_resources,
)

register.check_plugin(
    name="kube_cpu_usage",
    service_name="CPU resources",
    sections=["kube_performance_cpu", "kube_cpu_resources"],
    check_ruleset_name="kube_cpu_usage",
    discovery_function=discovery_kube_cpu,
    check_function=check_kube_cpu,
    check_default_parameters=DEFAULT_PARAMS,
)
