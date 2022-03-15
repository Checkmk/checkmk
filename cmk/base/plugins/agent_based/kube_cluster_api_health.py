#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.kube import ClusterDetails


def parse(string_table: StringTable) -> ClusterDetails:
    return ClusterDetails(**json.loads(string_table[0][0]))


def discovery(section: ClusterDetails) -> DiscoveryResult:
    yield Service()


def check(section: ClusterDetails) -> CheckResult:
    api_health = section.api_health
    name_and_health = [("live", api_health.live), ("ready", api_health.ready)]
    for name, health in name_and_health:
        if health.status_code == 200:
            yield Result(state=State.OK, summary=name.title())
            continue
        yield Result(state=State.CRIT, summary=f"Not {name}")
        if health.verbose_response:
            yield Result(
                state=State.OK,
                notice=f"{name.title()} verbose response:\n{health.verbose_response}",
            )

    if not all(h.status_code == 200 for _, h in name_and_health):
        yield Result(state=State.OK, summary="See service details for more information")


register.agent_section(
    name="kube_cluster_details_v1",
    parse_function=parse,
    parsed_section_name="kube_cluster_api_health",
)

register.check_plugin(
    name="kube_cluster_api_health",
    service_name="Kubernetes API",
    discovery_function=discovery,
    check_function=check,
)
