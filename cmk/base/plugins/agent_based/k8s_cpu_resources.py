#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import time
from typing import Dict

from .agent_based_api.v1 import (
    check_levels,
    get_rate,
    get_value_store,
    register,
    render,
    Result,
    Service,
    State,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


def parse_k8s(string_table: StringTable):
    return json.loads(string_table[0][0])


register.agent_section(
    name="k8s_cpu_resources",
    parse_function=parse_k8s,
)

register.agent_section(
    name="k8s_live_cpu_usage_total",
    parse_function=parse_k8s,
)


def discovery_kubernetes_cpu_resources(
    section_k8s_cpu_resources, section_k8s_live_cpu_usage_total
) -> DiscoveryResult:
    if section_k8s_cpu_resources:
        yield Service()


def check_kubernetes_cpu_resources(
    section_k8s_cpu_resources, section_k8s_live_cpu_usage_total
) -> CheckResult:

    # https://github.com/google/cadvisor/issues/2026
    # https://stackoverflow.com/questions/34923788/prometheus-convert-cpu-user-seconds-to-cpu-usage
    if section_k8s_live_cpu_usage_total:
        yield from _determine_pod_cpu_usage(section_k8s_live_cpu_usage_total)

    # TODO: link usage to limit
    yield Result(state=State.OK, summary=f"Limit: {section_k8s_cpu_resources['limit']}")
    yield Result(state=State.OK, summary=f"Requests: {section_k8s_cpu_resources['requests']}")


def _determine_pod_cpu_usage(containers: Dict[str, float]):
    value_store = get_value_store()
    usage = 0.0
    for container, cpu_usage in containers.items():
        usage += get_rate(
            value_store, container, time.time(), cpu_usage * 10 ** (-9), raise_overflow=True
        )
    yield from check_levels(
        usage * 100,
        render_func=render.percent,
        label="Usage",
    )


register.check_plugin(
    name="k8s_cpu_resources",
    service_name="CPU Resources",
    sections=["k8s_cpu_resources", "k8s_live_cpu_usage_total"],
    discovery_function=discovery_kubernetes_cpu_resources,
    check_function=check_kubernetes_cpu_resources,
)
