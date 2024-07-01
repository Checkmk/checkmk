#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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
from cmk.plugins.kube.schemata.section import PodLifeCycle


def parse_kube_pod_lifecycle(string_table: StringTable) -> PodLifeCycle:
    """
    >>> parse_kube_pod_lifecycle([['{"phase": "running"}']])
    PodLifeCycle(phase=<Phase.RUNNING: 'running'>)
    """
    return PodLifeCycle.model_validate_json(string_table[0][0])


agent_section_kube_pod_lifecycle_v1 = AgentSection(
    name="kube_pod_lifecycle_v1",
    parse_function=parse_kube_pod_lifecycle,
    parsed_section_name="kube_pod_lifecycle",
)


def discovery_kube_pod_phase(section: PodLifeCycle) -> DiscoveryResult:
    yield Service()


def check_kube_pod_phase(section: PodLifeCycle) -> CheckResult:
    yield Result(state=State.OK, summary=section.phase.title())


check_plugin_kube_pod_phase = CheckPlugin(
    name="kube_pod_phase",
    service_name="Phase",
    sections=["kube_pod_lifecycle"],
    discovery_function=discovery_kube_pod_phase,
    check_function=check_kube_pod_phase,
)
