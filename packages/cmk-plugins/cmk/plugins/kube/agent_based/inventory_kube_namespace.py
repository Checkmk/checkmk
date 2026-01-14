#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Attributes, InventoryPlugin, InventoryResult
from cmk.plugins.kube.schemata.section import NamespaceInfo


def inventorize_kube_namespace(
    section: NamespaceInfo,
) -> InventoryResult:
    yield Attributes(
        path=["software", "applications", "kube", "metadata"],
        inventory_attributes={
            "object": "Namespace",
            "name": section.name,
            "namespace": section.name,
        },
    )


inventory_plugin_kube_namespace = InventoryPlugin(
    name="kube_namespace",
    sections=["kube_namespace_info"],
    inventory_function=inventorize_kube_namespace,
)
