#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Optional

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, register, TableRow
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import InventoryResult
from cmk.base.plugins.agent_based.utils.k8s import KubeletInfo, NodeInfo


def inventory_kube_node(
    section_kube_node_info: Optional[NodeInfo],
    section_kube_node_kubelet: Optional[KubeletInfo],
) -> InventoryResult:
    if section_kube_node_info is None or section_kube_node_kubelet is None:
        return
    yield Attributes(
        path=["software", "applications", "kube", "node"],
        inventory_attributes={
            "name": section_kube_node_info.name,
            "operating_system": section_kube_node_info.operating_system,
            "os_image": section_kube_node_info.os_image,
            "kernel_version": section_kube_node_info.kernel_version,
            "architecture": section_kube_node_info.architecture,
            "container_runtime_version": section_kube_node_info.container_runtime_version,
            "kubelet_version": section_kube_node_kubelet.version,
            "kube_proxy_version": section_kube_node_kubelet.proxy_version,
        },
    )
    for label in section_kube_node_info.labels.values():
        yield TableRow(
            path=["software", "applications", "kube", "labels"],
            key_columns={"label_name": label.name},
            inventory_columns={"label_value": label.value},
        )


register.inventory_plugin(
    name="kube_node",
    sections=["kube_node_info", "kube_node_kubelet"],
    inventory_function=inventory_kube_node,
)
