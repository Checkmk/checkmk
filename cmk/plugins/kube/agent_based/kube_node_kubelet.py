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
from cmk.plugins.kube.schemata.api import NodeConnectionError
from cmk.plugins.kube.schemata.section import KubeletInfo


def parse_kube_node_kubelet_v1(string_table: StringTable) -> KubeletInfo:
    return KubeletInfo.model_validate_json(string_table[0][0])


def check_kube_node_kubelet(section: KubeletInfo) -> CheckResult:
    # The conversion of the status code is based on:
    # https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#container-probes
    if isinstance(section.health, NodeConnectionError):
        yield Result(state=State.CRIT, summary="Unresponsive Node")
        yield Result(
            state=State.OK,
            notice=f"Verbose response:\n{section.health.message}",
        )
    elif section.health.status_code == 200:
        yield Result(state=State.OK, summary="Healthy")
    else:
        yield Result(state=State.CRIT, summary="Not healthy")
        if section.health.response:
            yield Result(
                state=State.OK,
                notice=f"Verbose response:\n{section.health.response}",
            )
    yield Result(state=State.OK, summary=f"Version {section.version}")


def discover_kube_node_kubelet(section: KubeletInfo) -> DiscoveryResult:
    yield Service()


check_plugin_kube_node_kubelet = CheckPlugin(
    name="kube_node_kubelet",
    sections=["kube_node_kubelet"],
    discovery_function=discover_kube_node_kubelet,
    check_function=check_kube_node_kubelet,
    service_name="Kubelet",
)

agent_section_kube_node_kubelet_v1 = AgentSection(
    name="kube_node_kubelet_v1",
    parsed_section_name="kube_node_kubelet",
    parse_function=parse_kube_node_kubelet_v1,
)
