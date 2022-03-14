#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Dict, Mapping

from .agent_based_api.v1 import check_levels, HostLabel, register, Service, TableRow
from .agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    HostLabelGenerator,
    InventoryResult,
)
from .utils import k8s

Section = Dict

###########################################################################
# NOTE: This check (and associated special agent) is deprecated and will be
#       removed in Checkmk version 2.2.
###########################################################################


def host_labels(section: Dict) -> HostLabelGenerator:
    if section:
        yield HostLabel("cmk/kubernetes_object", "cluster")
        yield HostLabel("cmk/kubernetes", "yes")


register.agent_section(
    name="k8s_nodes",
    parse_function=k8s.parse_json,
    host_label_function=host_labels,
)


def discover_k8s_nodes(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_k8s_nodes(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from check_levels(
        len(section.get("nodes", [])),
        metric_name="k8s_nodes",
        levels_upper=params.get("levels"),
        levels_lower=params.get("levels_lower"),
        render_func=lambda x: str(int(x)),
        label="Number of nodes",
        boundaries=(0, None),
    )


register.check_plugin(
    name="k8s_nodes",
    service_name="Nodes",
    discovery_function=discover_k8s_nodes,
    check_function=check_k8s_nodes,
    check_ruleset_name="k8s_nodes",
    check_default_parameters={},
)


def inventory_k8s_nodes(section: Section) -> InventoryResult:
    path = ["software", "applications", "kubernetes", "nodes"]
    for k8s_node in section.get("nodes", []):
        # ONLY status data::little trick: key_columns and *_columns should not have common keys.
        # key_columns are used to identify a row.
        yield TableRow(
            path=path,
            key_columns={
                "id": k8s_node,
            },
            inventory_columns={},
            status_columns={
                "name": k8s_node,
            },
        )


register.inventory_plugin(
    name="k8s_nodes",
    inventory_function=inventory_k8s_nodes,
)
