#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Attributes, InventoryPlugin, InventoryResult
from cmk.plugins.kube.kube_inventory import (
    labels_to_table,
    match_expressions_to_str,
    match_labels_to_str,
)
from cmk.plugins.kube.kube_strategy import strategy_text
from cmk.plugins.kube.schemata.section import DeploymentInfo, UpdateStrategy


def inventorize_kube_deployment(
    section_kube_deployment_info: DeploymentInfo | None,
    section_kube_update_strategy: UpdateStrategy | None,
) -> InventoryResult:
    if section_kube_deployment_info is None or section_kube_update_strategy is None:
        return
    yield Attributes(
        path=["software", "applications", "kube", "metadata"],
        inventory_attributes={
            "object": "Deployment",
            "name": section_kube_deployment_info.name,
            "namespace": section_kube_deployment_info.namespace,
        },
    )
    selector = section_kube_deployment_info.selector
    yield Attributes(
        path=["software", "applications", "kube", "deployment"],
        inventory_attributes={
            "strategy": strategy_text(section_kube_update_strategy.strategy),
            "match_labels": match_labels_to_str(selector.match_labels),
            "match_expressions": match_expressions_to_str(selector.match_expressions),
        },
    )
    yield from labels_to_table(section_kube_deployment_info.labels)


inventory_plugin_kube_deployment = InventoryPlugin(
    name="kube_deployment",
    sections=["kube_deployment_info", "kube_update_strategy"],
    inventory_function=inventorize_kube_deployment,
)
