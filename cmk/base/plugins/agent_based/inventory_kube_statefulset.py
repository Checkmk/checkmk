#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, register
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import InventoryResult
from cmk.base.plugins.agent_based.utils.kube import StatefulSetInfo, UpdateStrategy
from cmk.base.plugins.agent_based.utils.kube_inventory import (
    labels_to_table,
    match_expressions_to_str,
    match_labels_to_str,
)
from cmk.base.plugins.agent_based.utils.kube_strategy import strategy_text


def inventory_kube_statefulset(
    section_kube_statefulset_info: Optional[StatefulSetInfo],
    section_kube_update_strategy: Optional[UpdateStrategy],
) -> InventoryResult:
    if section_kube_statefulset_info is None or section_kube_update_strategy is None:
        return
    yield Attributes(
        path=["software", "applications", "kube", "metadata"],
        inventory_attributes={
            "object": "StatefulSet",
            "name": section_kube_statefulset_info.name,
            "namespace": section_kube_statefulset_info.namespace,
        },
    )
    selector = section_kube_statefulset_info.selector
    yield Attributes(
        path=["software", "applications", "kube", "statefulset"],
        inventory_attributes={
            "strategy": strategy_text(section_kube_update_strategy.strategy),
            "match_labels": match_labels_to_str(selector.match_labels),
            "match_expressions": match_expressions_to_str(selector.match_expressions),
        },
    )
    yield from labels_to_table(section_kube_statefulset_info.labels)


register.inventory_plugin(
    name="kube_statefulset",
    sections=["kube_statefulset_info", "kube_update_strategy"],
    inventory_function=inventory_kube_statefulset,
)
