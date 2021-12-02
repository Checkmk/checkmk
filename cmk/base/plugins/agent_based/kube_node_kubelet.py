#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.k8s import KubeletInfo


def parse_kube_node_kubelet_v1(string_table: StringTable) -> KubeletInfo:
    return KubeletInfo(**json.loads(string_table[0][0]))


def check_k8s_node_kubelet(section: KubeletInfo) -> CheckResult:
    # The conversion of the status code is based on:
    # https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#container-probes
    yield Result(state=State.OK, summary=f"Version {section.version}")
    yield Result(
        state=State.OK if section.health.status_code == 200 else State.CRIT,
        summary="Health check response is %s" % section.health.response.replace("\n", ""),
        details=section.health.verbose_response,
    )


def discover_k8s_node_kubelet(section: KubeletInfo) -> DiscoveryResult:
    yield Service()


register.check_plugin(
    name="kube_node_kubelet",
    sections=["kube_node_kubelet"],
    discovery_function=discover_k8s_node_kubelet,
    check_function=check_k8s_node_kubelet,
    service_name="Kubelet",
)

register.agent_section(
    name="kube_node_kubelet_v1",
    parsed_section_name="kube_node_kubelet",
    parse_function=parse_kube_node_kubelet_v1,
)
