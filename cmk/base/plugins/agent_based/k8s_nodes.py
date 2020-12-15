#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Dict, Mapping

from .agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    HostLabelGenerator,
)
from .agent_based_api.v1 import check_levels, HostLabel, register, Service

from .utils import k8s


def host_labels(section: Dict) -> HostLabelGenerator:
    if section:
        yield HostLabel(u'cmk/kubernetes_object', u'master')


register.agent_section(
    name="k8s_nodes",
    parse_function=k8s.parse_json,
    host_label_function=host_labels,
)


def discover_k8s_nodes(section: Dict) -> DiscoveryResult:
    if section:
        yield Service()


def check_k8s_nodes(params: Mapping[str, Any], section: Dict) -> CheckResult:
    yield from check_levels(  # type: ignore[call-overload]  # yes, it's tuples in the params.
        len(section.get('nodes', [])),
        metric_name='k8s_nodes',
        levels_upper=params.get('levels'),
        levels_lower=params.get('levels_lower'),
        render_func=lambda x: str(int(x)),
        label='Number of nodes',
    )


register.check_plugin(
    name="k8s_nodes",
    service_name="Nodes",
    discovery_function=discover_k8s_nodes,
    check_function=check_k8s_nodes,
    check_ruleset_name="k8s_nodes",
    check_default_parameters={},
)
