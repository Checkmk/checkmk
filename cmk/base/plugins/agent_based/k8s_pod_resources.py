#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

from .agent_based_api.v1 import Metric, register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.k8s import PodResources


def parse_k8s(string_table: StringTable):
    return PodResources(**json.loads(string_table[0][0]))


register.agent_section(
    name="k8s_pod_resources",
    parse_function=parse_k8s,
)


def discovery_kubernetes_pod_resources(section: PodResources) -> DiscoveryResult:
    yield Service()


def check_kubernetes_pod_resources(section: PodResources) -> CheckResult:
    for resource, value in section.dict().items():
        if value is None:  # some k8 objects do not have allocatable, capacity
            continue
        yield Result(state=State.OK, summary=f"{resource}: {value}")
        if resource in ("capacity", "pending", "running", "allocatable"):
            yield Metric(name=f"k8s_pods_{resource}", value=value)


register.check_plugin(
    name="k8s_pod_resources",
    service_name="Pod Resources",
    discovery_function=discovery_kubernetes_pod_resources,
    check_function=check_kubernetes_pod_resources,
)
