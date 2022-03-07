#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, register, TableRow
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import InventoryResult
from cmk.base.plugins.agent_based.utils.k8s import DaemonSetInfo
from cmk.base.plugins.agent_based.utils.kube_inventory import (
    match_expressions_to_str,
    match_labels_to_str,
)


def inventory_kube_daemonset(
    section: DaemonSetInfo,
) -> InventoryResult:
    selector = section.selector
    yield Attributes(
        path=["software", "applications", "kube", "daemonset"],
        inventory_attributes={
            "name": section.name,
            "namespace": section.namespace,
            "match_labels": match_labels_to_str(selector.match_labels),
            "match_expressions": match_expressions_to_str(selector.match_expressions),
        },
    )
    for label in section.labels.values():
        yield TableRow(
            path=["software", "applications", "kube", "labels"],
            key_columns={"label_name": label.name},
            inventory_columns={"label_value": label.value},
        )


register.inventory_plugin(
    name="kube_daemonset",
    sections=["kube_daemonset_info"],
    inventory_function=inventory_kube_daemonset,
)
