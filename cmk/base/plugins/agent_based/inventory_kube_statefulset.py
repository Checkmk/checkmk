#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, register
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import InventoryResult
from cmk.base.plugins.agent_based.utils.k8s import StatefulSetInfo
from cmk.base.plugins.agent_based.utils.kube_inventory import (
    labels_to_table,
    match_expressions_to_str,
    match_labels_to_str,
)


def inventory_kube_statefulset(section: StatefulSetInfo) -> InventoryResult:
    selector = section.selector
    yield Attributes(
        path=["software", "applications", "kube", "statefulset"],
        inventory_attributes={
            "name": section.name,
            "namespace": section.namespace,
            "match_labels": match_labels_to_str(selector.match_labels),
            "match_expressions": match_expressions_to_str(selector.match_expressions),
        },
    )
    yield from labels_to_table(section.labels)


register.inventory_plugin(
    name="kube_statefulset",
    sections=["kube_statefulset_info"],
    inventory_function=inventory_kube_statefulset,
)
