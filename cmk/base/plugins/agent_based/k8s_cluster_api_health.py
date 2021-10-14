#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.k8s import ClusterInfo


def parse(string_table: StringTable) -> ClusterInfo:
    return ClusterInfo(**json.loads(string_table[0][0]))


def discovery(section: ClusterInfo) -> DiscoveryResult:
    yield Service()


def check(section: ClusterInfo) -> CheckResult:
    api_health = section.api_health
    for name, health in [("Readiness", api_health.ready), ("Liveness", api_health.live)]:
        state = State.OK
        message = f"{name} probe {health.response}"
        if health.status_code != 200:
            state = State.CRIT
            if health.verbose_response:
                yield Result(state=State.OK, notice=health.verbose_response)
        yield Result(state=state, summary=message)


register.agent_section(
    name="k8s_cluster_details_v1",
    parse_function=parse,
    parsed_section_name="k8s_cluster_api_health",
)

register.check_plugin(
    name="k8s_cluster_api_health",
    service_name="Cluster API",
    discovery_function=discovery,
    check_function=check,
)
