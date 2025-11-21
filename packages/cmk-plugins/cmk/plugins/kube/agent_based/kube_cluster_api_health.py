#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.kube.schemata.section import ClusterDetails


def parse(string_table: StringTable) -> ClusterDetails:
    return ClusterDetails.model_validate_json(string_table[0][0])


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
        yield Result(
            state=State.OK,
            notice=f"{name.title()} response:\n{health.response}",
        )

    if not all(h.status_code == 200 for _, h in name_and_health):
        yield Result(state=State.OK, summary="See service details for more information")


agent_section_kube_cluster_details_v1 = AgentSection(
    name="kube_cluster_details_v1",
    parse_function=parse,
    parsed_section_name="kube_cluster_api_health",
)

check_plugin_kube_cluster_api_health = CheckPlugin(
    name="kube_cluster_api_health",
    service_name="Kubernetes API",
    discovery_function=discovery,
    check_function=check,
)
